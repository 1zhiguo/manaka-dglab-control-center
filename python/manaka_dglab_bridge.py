"""Embedded DG-LAB Socket server and safety-gated output adapter.

The mobile app connects to the local WebSocket server through the QR URL.  An
internal controller client uses the same public protocol as the reference web
controller, which keeps the bridge easy to test and compatible with DG-LAB's
Socket mode.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import math
import queue
import re
import socket
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Iterable
from functools import lru_cache

import websockets
from manaka_wave_player import ChannelPlayer


DEFAULT_PORT = 9999
HEARTBEAT_SECONDS = 25.0


def clamp_strength(value: float, hard_cap: int = 200) -> int:
    """Clamp a UI strength to the user's 0..200 channel range."""
    if not math.isfinite(float(value)) or not math.isfinite(float(hard_cap)):
        return 0
    cap = max(0, min(200, int(hard_cap)))
    return max(0, min(cap, int(round(float(value)))))


def strength_message(channel: str, value: float, hard_cap: int = 200) -> str:
    channel_code = "2" if str(channel).upper() == "B" else "1"
    return f"strength-{channel_code}+2+{clamp_strength(value, hard_cap)}"


def pulse_message(channel: str, frames: Iterable[str]) -> str:
    clean: list[str] = []
    for frame in frames:
        value = str(frame).upper()
        if len(value) != 16 or any(char not in "0123456789ABCDEF" for char in value):
            raise ValueError("DG-LAB waveform frames must be 16 hexadecimal characters")
        values = bytes.fromhex(value)
        if any(not 10 <= code <= 240 for code in values[:4]) or any(amplitude > 100 for amplitude in values[4:]):
            raise ValueError("Invalid DG-LAB V3 frequency code or amplitude")
        clean.append(value)
    if not clean or len(clean) > 100:
        raise ValueError("DG-LAB waveform message must contain 1..100 frames")
    channel_name = "B" if str(channel).upper() == "B" else "A"
    return f"pulse-{channel_name}:{json.dumps(clean, separators=(',', ':'))}"


@lru_cache(maxsize=128)
def validate_stream(frames):
    for offset in range(0, len(frames), 100):
        pulse_message("A", frames[offset:offset+100])


def discover_lan_ips() -> tuple[str, ...]:
    """Return usable IPv4 addresses, with the default-route address first."""
    candidates: list[str] = []

    def add(address: str) -> None:
        try:
            parsed = ipaddress.ip_address(str(address))
        except ValueError:
            return
        if (not isinstance(parsed, ipaddress.IPv4Address) or parsed.is_loopback
                or parsed.is_link_local or parsed.is_unspecified or parsed.is_multicast):
            return
        value = str(parsed)
        if value not in candidates:
            candidates.append(value)

    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        add(probe.getsockname()[0])
    except OSError:
        pass
    finally:
        probe.close()

    try:
        for result in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            add(result[4][0])
    except OSError:
        pass
    return tuple(candidates)


def discover_lan_ip() -> str:
    """Return the preferred LAN address without sending internet traffic."""
    candidates = discover_lan_ips()
    return candidates[0] if candidates else "127.0.0.1"


@dataclass(frozen=True)
class BridgeSnapshot:
    server_ready: bool
    connected: bool
    controller_id: str
    target_id: str
    qr_url: str
    lan_ip: str
    port: int


class DGLabBridge:
    """Own a local Socket server and one internal controller connection."""

    def __init__(self, events: queue.Queue, *, port: int = DEFAULT_PORT, lan_ip: str = "") -> None:
        self.events = events
        self.requested_port = int(port)
        self.port = int(port)
        self.available_lan_ips = discover_lan_ips()
        requested_ip = str(lan_ip).strip()
        self.lan_ip = (
            requested_ip
            if requested_ip in self.available_lan_ips
            else self.available_lan_ips[0] if self.available_lan_ips else "127.0.0.1"
        )
        self.controller_id = ""
        self.target_id = ""
        self.qr_url = ""
        self.server_ready = False
        self.connected = False

        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop_event: asyncio.Event | None = None
        self._server = None
        self._controller_ws = None
        self._clients: dict[str, object] = {}
        self._relations: dict[str, str] = {}
        self._generation = 0
        self._auto_enabled = False
        self._desired_strength = {"A": 0, "B": 0}
        self._desired_frames: dict[str, tuple[str, ...]] = {"A": (), "B": ()}
        self._desired_wave_key = {"A": "", "B": ""}
        self._desired_loop = {"A": True, "B": True}
        self._desired_transition = {"A":"immediate", "B":"immediate"}
        self._hard_cap = 30
        self._channel_caps = {"A": 200, "B": 200}
        self._device_limits = {"A": 200, "B": 200}
        self._telemetry_received_at = 0.0
        self.telemetry_timeout = 1.0
        self._sent_strengths = {"A": 0, "B": 0}
        self.playback_state = {key: ("", "stopped") for key in "AB"}

    def _playback(self, channel, key, state):
        value = (key.split("|", 1)[0], state)
        if self.playback_state[channel] != value:
            self.playback_state[channel] = value
            self._emit("playback", channel=channel, wave=value[0], state=state)

    @property
    def auto_enabled(self) -> bool:
        return self._auto_enabled

    def channel_limit(self, channel: str) -> int:
        return self._device_limits[channel]

    def channel_output(self, channel: str) -> int:
        return self._sent_strengths[channel]

    def configure_limits(self, global_cap, cap_a, cap_b) -> None:
        limits = (clamp_strength(global_cap),clamp_strength(cap_a),clamp_strength(cap_b))
        def apply():
            self._hard_cap = limits[0]
            self._channel_caps = {"A":min(limits[0],limits[1]),"B":min(limits[0],limits[2])}
        loop = self._loop
        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(apply)
        else:
            apply()

    def zero_output(self) -> None:
        """Clear output immediately while retaining the user's resume choice."""
        loop = self._loop
        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(self._zero_in_loop)

    def _zero_in_loop(self) -> None:
        self._generation += 1
        self._desired_strength = {"A": 0, "B": 0}
        self._desired_frames = {"A": (), "B": ()}
        asyncio.create_task(self._safe_zero_async())

    def set_lan_ip(self, address: str) -> bool:
        """Regenerate the QR URL for another local adapter without restarting."""
        value = str(address).strip()
        if value not in self.available_lan_ips:
            return False
        self.lan_ip = value
        if self.controller_id:
            self.qr_url = self._build_qr_url()
            self._emit(
                "ready",
                qr_url=self.qr_url,
                lan_ip=self.lan_ip,
                port=self.port,
                controller_id=self.controller_id,
            )
        return True

    def _build_qr_url(self) -> str:
        return (
            "https://www.dungeon-lab.com/app-download.php#"
            f"DGLAB-SOCKET#ws://{self.lan_ip}:{self.port}/{self.controller_id}"
        )

    def snapshot(self) -> BridgeSnapshot:
        return BridgeSnapshot(
            self.server_ready,
            self.connected,
            self.controller_id,
            self.target_id,
            self.qr_url,
            self.lan_ip,
            self.port,
        )

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._thread_main, name="DGLabSocketBridge", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self.emergency_stop()
        loop = self._loop
        stop_event = self._stop_event
        if loop is not None and stop_event is not None and loop.is_running():
            loop.call_soon_threadsafe(stop_event.set)
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def set_auto_enabled(self, enabled: bool) -> None:
        loop = self._loop
        if loop is None or not loop.is_running():
            self._auto_enabled = False
            return
        loop.call_soon_threadsafe(self._set_auto_enabled_in_loop, bool(enabled))

    def update_auto_output(
        self,
        strength: float,
        frames: Iterable[str],
        *,
        wave_key: str,
        hard_cap: int,
    ) -> None:
        clean_frames = tuple(str(frame).upper() for frame in frames)
        # Validate before crossing threads so malformed custom data can never be sent.
        if clean_frames:
            validate_stream(clean_frames)
        loop = self._loop
        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(
                self._set_desired_in_loop,
                "A",
                clamp_strength(strength, hard_cap),
                clean_frames,
                str(wave_key),
                max(0, min(200, int(hard_cap))),
            )

    def update_auto_outputs(
        self,
        strength_a: float,
        frames_a: Iterable[str],
        *,
        wave_key_a: str,
        strength_b: float,
        frames_b: Iterable[str],
        wave_key_b: str,
        hard_cap: int,
        received_at: float | None = None,
        cap_a: float | None = None,
        cap_b: float | None = None,
        loop_a: bool = True,
        loop_b: bool = True,
        transition_a: str = "immediate",
        transition_b: str = "immediate",
    ) -> None:
        clean_a = tuple(str(frame).upper() for frame in frames_a)
        clean_b = tuple(str(frame).upper() for frame in frames_b)
        if clean_a:
            validate_stream(clean_a)
        if clean_b:
            validate_stream(clean_b)
        loop = self._loop
        if loop is not None and loop.is_running():
            safe_cap = max(0, min(200, int(hard_cap)))
            loop.call_soon_threadsafe(
                self._set_desired_outputs_in_loop,
                clamp_strength(strength_a, safe_cap),
                clean_a,
                str(wave_key_a),
                clamp_strength(strength_b, safe_cap),
                clean_b,
                str(wave_key_b),
                safe_cap,
                time.monotonic() if received_at is None else received_at,
                safe_cap if cap_a is None else clamp_strength(cap_a, safe_cap),
                safe_cap if cap_b is None else clamp_strength(cap_b, safe_cap),
                loop_a, loop_b, transition_a, transition_b, self._generation,
            )

    def manual_test(self, strength: int, frames: Iterable[str], *, hard_cap: int) -> bool:
        clean_frames = tuple(str(frame).upper() for frame in frames)[:10]
        if not clean_frames:
            return False
        pulse_message("A", clean_frames)
        loop = self._loop
        if loop is None or not loop.is_running() or not self.connected:
            return False
        safe_strength = min(10, clamp_strength(strength, hard_cap), self._channel_caps["A"], self._device_limits["A"])
        asyncio.run_coroutine_threadsafe(self._manual_test(safe_strength, clean_frames), loop)
        return True

    def emergency_stop(self) -> None:
        loop = self._loop
        if loop is None or not loop.is_running():
            self._auto_enabled = False
            return
        loop.call_soon_threadsafe(self._request_emergency_in_loop)

    def _thread_main(self) -> None:
        try:
            asyncio.run(self._run())
        except Exception as error:  # pragma: no cover - final guard for GUI process
            self._emit("error", detail=f"Socket 服务异常：{error}")

    async def _run(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._stop_event = asyncio.Event()
        try:
            self._server = await websockets.serve(
                self._server_handler,
                "0.0.0.0",
                self.requested_port,
                ping_interval=20,
                ping_timeout=20,
                max_size=1024 * 1024,
            )
        except OSError as error:
            if self.requested_port == 0:
                self._emit("error", detail=f"无法启动 Socket 服务：{error}")
                return
            # Windows may reserve a whole port range without a listening process.
            # Let the OS choose an available port; the QR always uses that port.
            try:
                self._server = await websockets.serve(
                    self._server_handler, "0.0.0.0", 0,
                    ping_interval=20, ping_timeout=20, max_size=1024 * 1024,
                )
            except OSError as fallback_error:
                self._emit("error", detail=f"无法启动 Socket 服务：{fallback_error}")
                return
            self._emit("port_changed", requested_port=self.requested_port)

        sockets = self._server.sockets or []
        if sockets:
            self.port = int(sockets[0].getsockname()[1])
        self.server_ready = True
        controller_task = asyncio.create_task(self._controller_client())
        output_task = asyncio.create_task(self._output_loop())
        await self._stop_event.wait()
        self._auto_enabled = False
        await self._safe_zero_async()
        for task in (output_task, controller_task):
            task.cancel()
        await asyncio.gather(output_task, controller_task, return_exceptions=True)
        self._server.close()
        await self._server.wait_closed()
        self.server_ready = False

    async def _server_handler(self, websocket) -> None:
        connection_id = str(uuid.uuid4())
        self._clients[connection_id] = websocket
        await websocket.send(
            json.dumps({"type": "bind", "clientId": connection_id, "targetId": "", "message": "targetId"})
        )
        try:
            async for raw in websocket:
                try:
                    packet = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    continue
                if packet.get("type") == "bind" and packet.get("message") == "DGLAB":
                    await self._handle_bind(websocket, connection_id, packet)
                elif packet.get("type") in {"msg", "heartbeat"}:
                    await self._forward_message(websocket, connection_id, packet)
        except websockets.ConnectionClosed:
            pass
        finally:
            peer = self._relations.pop(connection_id, None)
            self._clients.pop(connection_id, None)
            if peer:
                self._relations.pop(peer, None)
                peer_ws = self._clients.get(peer)
                if peer_ws is not None:
                    try:
                        await peer_ws.send(json.dumps({"type": "break", "clientId": connection_id, "targetId": peer, "message": "209"}))
                    except websockets.ConnectionClosed:
                        pass

    async def _handle_bind(self, websocket, connection_id: str, packet: dict) -> None:
        controller_id = str(packet.get("clientId", ""))
        phone_id = str(packet.get("targetId", ""))
        if connection_id not in {controller_id, phone_id}:
            return
        if self._clients.get(controller_id) is None or self._clients.get(phone_id) is None:
            await websocket.send(
                json.dumps({"type": "bind", "clientId": controller_id, "targetId": phone_id, "message": "401"})
            )
            return
        self._relations[controller_id] = phone_id
        self._relations[phone_id] = controller_id
        response = json.dumps({"type": "bind", "clientId": controller_id, "targetId": phone_id, "message": "200"})
        for client_id in (controller_id, phone_id):
            try:
                await self._clients[client_id].send(response)
            except websockets.ConnectionClosed:
                pass

    async def _forward_message(self, websocket, connection_id: str, packet: dict) -> None:
        first = str(packet.get("clientId", ""))
        second = str(packet.get("targetId", ""))
        if connection_id == first:
            peer = second
        elif connection_id == second:
            peer = first
        else:
            return
        if self._relations.get(connection_id) != peer:
            return
        target = self._clients.get(peer)
        if target is not None:
            try:
                await target.send(json.dumps(packet, separators=(",", ":")))
            except websockets.ConnectionClosed:
                pass

    async def _controller_client(self) -> None:
        uri = f"ws://127.0.0.1:{self.port}/"
        try:
            async with websockets.connect(uri, proxy=None, open_timeout=5, ping_interval=20, ping_timeout=20) as websocket:
                self._controller_ws = websocket
                hello = json.loads(await websocket.recv())
                self.controller_id = str(hello.get("clientId", ""))
                self.qr_url = self._build_qr_url()
                self._emit(
                    "ready",
                    qr_url=self.qr_url,
                    lan_ip=self.lan_ip,
                    port=self.port,
                    controller_id=self.controller_id,
                )
                async for raw in websocket:
                    packet = json.loads(raw)
                    packet_type = packet.get("type")
                    if packet_type == "bind" and str(packet.get("message")) == "200":
                        first = str(packet.get("clientId", ""))
                        second = str(packet.get("targetId", ""))
                        self.target_id = second if first == self.controller_id else first
                        self.connected = True
                        self._emit("connected", target_id=self.target_id)
                    elif packet_type == "break":
                        self._mark_disconnected()
                    elif packet_type == "msg":
                        feedback = str(packet.get("message", ""))
                        limits = re.fullmatch(r"strength-\d{1,3}\+\d{1,3}\+(\d{1,3})\+(\d{1,3})", feedback)
                        if limits:
                            previous = self._device_limits
                            self._device_limits = {"A": min(200, int(limits[1])), "B": min(200, int(limits[2]))}
                            if any(self._device_limits[key] < previous[key] for key in "AB"):
                                self._zero_in_loop()
                        self._emit("feedback", message=str(packet.get("message", "")))
        except asyncio.CancelledError:
            raise
        except Exception as error:
            if self._stop_event is None or not self._stop_event.is_set():
                self._emit("error", detail=f"控制连接异常：{error}")
        finally:
            self._controller_ws = None
            self._mark_disconnected()

    def _mark_disconnected(self) -> None:
        was_connected = self.connected
        self.connected = False
        for key in "AB":
            self._playback(key, "", "stopped")
        self.target_id = ""
        self._auto_enabled = False
        self._device_limits = {"A": 200, "B": 200}
        self._telemetry_received_at = 0
        self._desired_strength = {"A": 0, "B": 0}
        if was_connected:
            self._sent_strengths = {"A": 0, "B": 0}
            self._emit("disconnected")

    def _set_auto_enabled_in_loop(self, enabled: bool) -> None:
        self._generation += 1
        self._auto_enabled = bool(enabled and self.connected)
        self._desired_strength = {"A": 0, "B": 0}
        self._desired_frames = {"A": (), "B": ()}
        if not self._auto_enabled:
            asyncio.create_task(self._safe_zero_async())

    def _set_desired_in_loop(
        self, channel: str, strength: int, frames: tuple[str, ...], wave_key: str, hard_cap: int
    ) -> None:
        channel = "B" if channel == "B" else "A"
        self._desired_strength[channel] = clamp_strength(strength, hard_cap)
        self._desired_frames[channel] = frames
        self._desired_wave_key[channel] = wave_key
        self._hard_cap = hard_cap
        self._telemetry_received_at = time.monotonic()

    def _set_desired_outputs_in_loop(
        self,
        strength_a: int,
        frames_a: tuple[str, ...],
        wave_key_a: str,
        strength_b: int,
        frames_b: tuple[str, ...],
        wave_key_b: str,
        hard_cap: int,
        received_at: float | None = None,
        cap_a: int | None = None,
        cap_b: int | None = None,
        loop_a: bool = True,
        loop_b: bool = True,
        transition_a: str = "immediate",
        transition_b: str = "immediate",
        generation: int | None = None,
    ) -> None:
        if generation is not None and generation != self._generation:
            return
        stamp = time.monotonic() if received_at is None else received_at
        if stamp < self._telemetry_received_at:
            return
        if time.monotonic()-stamp >= self.telemetry_timeout:
            self._zero_in_loop()
            return
        self._channel_caps = {"A": hard_cap if cap_a is None else cap_a,
                              "B": hard_cap if cap_b is None else cap_b}
        self._set_desired_in_loop("A", strength_a, frames_a, wave_key_a, hard_cap)
        self._set_desired_in_loop("B", strength_b, frames_b, wave_key_b, hard_cap)
        self._telemetry_received_at = stamp
        self._desired_loop = {"A": loop_a, "B": loop_b}
        self._desired_transition = {"A":transition_a, "B":transition_b}

    def _request_emergency_in_loop(self) -> None:
        self._generation += 1
        self._auto_enabled = False
        self._desired_strength = {"A": 0, "B": 0}
        self._desired_frames = {"A": (), "B": ()}
        self._desired_wave_key = {"A": "", "B": ""}
        asyncio.create_task(self._safe_zero_async())

    async def _send_message(self, message: str) -> bool:
        if not self.connected or self._controller_ws is None or not self.target_id:
            return False
        packet = {
            "type": "msg",
            "clientId": self.controller_id,
            "targetId": self.target_id,
            "message": message,
        }
        try:
            await self._controller_ws.send(json.dumps(packet, separators=(",", ":")))
            strength = re.fullmatch(r"strength-([12])\+2\+(\d+)",message)
            if strength:
                self._sent_strengths["A" if strength[1] == "1" else "B"] = int(strength[2])
            return True
        except websockets.ConnectionClosed:
            self._mark_disconnected()
            return False

    async def _safe_zero_async(self) -> None:
        for key in "AB":
            self._playback(key, "", "stopped")
        if not self.connected:
            return
        await self._send_message(strength_message("A", 0))
        await self._send_message(strength_message("B", 0))
        await self._send_message("clear-1")
        await self._send_message("clear-2")

    async def _manual_test(self, strength: int, frames: tuple[str, ...]) -> None:
        self._generation += 1
        generation = self._generation
        self._auto_enabled = False
        await self._safe_zero_async()
        if generation != self._generation or not self.connected:
            return
        await self._send_message(strength_message("A", strength, min(10, self._hard_cap, self._channel_caps["A"], self._device_limits["A"])))
        await asyncio.sleep(0.15)
        if generation != self._generation or not self.connected:
            return
        await self._send_message(pulse_message("A", frames))
        self._emit("test_started", strength=strength)
        await asyncio.sleep(1.0)
        if generation == self._generation:
            await self._safe_zero_async()
            self._emit("test_finished")

    async def _output_loop(self) -> None:
        last_strength = {"A": None, "B": None}
        players = {key: ChannelPlayer() for key in "AB"}
        last_generation = -1
        last_heartbeat = 0.
        stale_reported = False
        while True:
            await asyncio.sleep(.025)
            now = time.monotonic()
            if self._generation != last_generation or not self.connected or not self._auto_enabled:
                for player in players.values():
                    player.reset()
                last_strength = {"A": None, "B": None}
                last_generation = self._generation
            if not self.connected or not self._auto_enabled:
                continue
            if self._telemetry_received_at and now-self._telemetry_received_at >= self.telemetry_timeout:
                if not stale_reported:
                    await self._safe_zero_async()
                    self._desired_strength = {"A": 0, "B": 0}
                    self._desired_frames = {"A": (), "B": ()}
                    self._emit("telemetry_stale")
                    stale_reported = True
                for player in players.values():
                    player.reset()
                last_strength = {"A": None, "B": None}
                continue
            stale_reported = False
            for channel in "AB":
                generation = self._generation
                cap = min(self._hard_cap, self._channel_caps[channel], self._device_limits[channel])
                strength = clamp_strength(self._desired_strength[channel], cap)
                plan = players[channel].plan(now, self._desired_wave_key[channel],
                    self._desired_frames[channel], self._desired_loop[channel], strength > 0, self._desired_transition[channel])
                if plan.finished:
                    strength = 0
                    self._playback(channel, self._desired_wave_key[channel], "finished")
                if plan.clear:
                    self._playback(channel, self._desired_wave_key[channel], "switching" if strength > 0 else "stopped")
                    await self._send_message("clear-1" if channel == "A" else "clear-2")
                if generation != self._generation or not self._auto_enabled or not self.connected:
                    continue
                cap = min(self._hard_cap, self._channel_caps[channel], self._device_limits[channel])
                strength = min(strength, clamp_strength(self._desired_strength[channel], cap))
                if strength != last_strength[channel]:
                    await self._send_message(strength_message(channel, strength, cap))
                    last_strength[channel] = strength
                if plan.frames and generation == self._generation and self._auto_enabled and self.connected:
                    if await self._send_message(pulse_message(channel, plan.frames)):
                        self._playback(channel, players[channel].identity[0], "playing")
            if now-last_heartbeat >= HEARTBEAT_SECONDS:
                await self._send_message("heartbeat")
                last_heartbeat = now

    def _emit(self, event: str, **payload) -> None:
        self.events.put(("dglab", {"event": event, **payload}))

