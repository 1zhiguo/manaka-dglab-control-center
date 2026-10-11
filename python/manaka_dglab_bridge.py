"""Embedded DG-LAB Socket server and safety-gated output adapter.

The mobile app connects to the local WebSocket server through the QR URL.  An
internal controller client uses the same public protocol as the reference web
controller, which keeps the bridge easy to test and compatible with DG-LAB's
Socket mode.
"""

from __future__ import annotations

import asyncio
import json
import queue
import socket
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Iterable

import websockets


DEFAULT_PORT = 9999
HEARTBEAT_SECONDS = 25.0
WAVE_CHUNK_SECONDS = 0.8
WAVE_CLEAR_SETTLE_SECONDS = 0.15


def clamp_strength(value: float, hard_cap: int = 100) -> int:
    """Clamp a UI strength to the user's 0..100 safety range."""
    cap = max(0, min(100, int(hard_cap)))
    return max(0, min(cap, int(round(float(value)))))


def strength_message(channel: str, value: float, hard_cap: int = 100) -> str:
    channel_code = "2" if str(channel).upper() == "B" else "1"
    return f"strength-{channel_code}+2+{clamp_strength(value, hard_cap)}"


def pulse_message(channel: str, frames: Iterable[str]) -> str:
    clean: list[str] = []
    for frame in frames:
        value = str(frame).upper()
        if len(value) != 16 or any(char not in "0123456789ABCDEF" for char in value):
            raise ValueError("DG-LAB waveform frames must be 16 hexadecimal characters")
        clean.append(value)
    if not clean or len(clean) > 100:
        raise ValueError("DG-LAB waveform message must contain 1..100 frames")
    channel_name = "B" if str(channel).upper() == "B" else "A"
    return f"pulse-{channel_name}:{json.dumps(clean, separators=(',', ':'))}"


def discover_lan_ip() -> str:
    """Return the preferred LAN address without sending internet traffic."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        address = probe.getsockname()[0]
        if address and not address.startswith("127."):
            return address
    except OSError:
        pass
    finally:
        probe.close()
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "127.0.0.1"


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

    def __init__(self, events: queue.Queue, *, port: int = DEFAULT_PORT) -> None:
        self.events = events
        self.requested_port = int(port)
        self.port = int(port)
        self.lan_ip = discover_lan_ip()
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
        self._hard_cap = 30

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
            pulse_message("A", clean_frames[:100])
        loop = self._loop
        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(
                self._set_desired_in_loop,
                "A",
                clamp_strength(strength, hard_cap),
                clean_frames,
                str(wave_key),
                max(0, min(100, int(hard_cap))),
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
    ) -> None:
        clean_a = tuple(str(frame).upper() for frame in frames_a)
        clean_b = tuple(str(frame).upper() for frame in frames_b)
        if clean_a:
            pulse_message("A", clean_a[:100])
        if clean_b:
            pulse_message("B", clean_b[:100])
        loop = self._loop
        if loop is not None and loop.is_running():
            safe_cap = max(0, min(100, int(hard_cap)))
            loop.call_soon_threadsafe(
                self._set_desired_outputs_in_loop,
                clamp_strength(strength_a, safe_cap),
                clean_a,
                str(wave_key_a),
                clamp_strength(strength_b, safe_cap),
                clean_b,
                str(wave_key_b),
                safe_cap,
            )

    def manual_test(self, strength: int, frames: Iterable[str], *, hard_cap: int) -> bool:
        clean_frames = tuple(str(frame).upper() for frame in frames)[:10]
        if not clean_frames:
            return False
        pulse_message("A", clean_frames)
        loop = self._loop
        if loop is None or not loop.is_running() or not self.connected:
            return False
        safe_strength = min(10, clamp_strength(strength, hard_cap))
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
            self._emit("error", detail=f"无法监听端口 {self.requested_port}：{error}")
            return

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
            async with websockets.connect(uri, ping_interval=20, ping_timeout=20) as websocket:
                self._controller_ws = websocket
                hello = json.loads(await websocket.recv())
                self.controller_id = str(hello.get("clientId", ""))
                self.qr_url = (
                    "https://www.dungeon-lab.com/app-download.php#"
                    f"DGLAB-SOCKET#ws://{self.lan_ip}:{self.port}/{self.controller_id}"
                )
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
        self.target_id = ""
        self._auto_enabled = False
        if was_connected:
            self._emit("disconnected")

    def _set_auto_enabled_in_loop(self, enabled: bool) -> None:
        self._generation += 1
        self._auto_enabled = bool(enabled and self.connected)
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

    def _set_desired_outputs_in_loop(
        self,
        strength_a: int,
        frames_a: tuple[str, ...],
        wave_key_a: str,
        strength_b: int,
        frames_b: tuple[str, ...],
        wave_key_b: str,
        hard_cap: int,
    ) -> None:
        self._set_desired_in_loop("A", strength_a, frames_a, wave_key_a, hard_cap)
        self._set_desired_in_loop("B", strength_b, frames_b, wave_key_b, hard_cap)

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
            return True
        except websockets.ConnectionClosed:
            self._mark_disconnected()
            return False

    async def _safe_zero_async(self) -> None:
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
        await self._send_message(strength_message("A", strength, min(10, self._hard_cap)))
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
        last_strength: dict[str, int | None] = {"A": None, "B": None}
        last_wave_key = {"A": "", "B": ""}
        frame_cursor = {"A": 0, "B": 0}
        last_wave_send = {"A": 0.0, "B": 0.0}
        last_heartbeat = 0.0
        while True:
            await asyncio.sleep(0.1)
            if not self.connected or not self._auto_enabled:
                last_strength = {"A": None, "B": None}
                last_wave_key = {"A": "", "B": ""}
                frame_cursor = {"A": 0, "B": 0}
                continue
            now = time.monotonic()
            for channel in ("A", "B"):
                clear_message = "clear-2" if channel == "B" else "clear-1"
                strength = clamp_strength(self._desired_strength[channel], self._hard_cap)
                if strength != last_strength[channel]:
                    await self._send_message(strength_message(channel, strength, self._hard_cap))
                    last_strength[channel] = strength
                if strength <= 0 or not self._desired_frames[channel]:
                    if last_wave_key[channel]:
                        await self._send_message(clear_message)
                        last_wave_key[channel] = ""
                        frame_cursor[channel] = 0
                    continue
                if self._desired_wave_key[channel] != last_wave_key[channel]:
                    await self._send_message(clear_message)
                    last_wave_key[channel] = self._desired_wave_key[channel]
                    frame_cursor[channel] = 0
                    last_wave_send[channel] = 0.0
                    # DG-LAB recommends leaving a short gap after clearing the
                    # App queue to avoid erasing the first replacement block.
                    await asyncio.sleep(WAVE_CLEAR_SETTLE_SECONDS)
                    if (
                        not self.connected
                        or not self._auto_enabled
                        or self._desired_wave_key[channel] != last_wave_key[channel]
                    ):
                        continue
                    now = time.monotonic()
                if now - last_wave_send[channel] >= WAVE_CHUNK_SECONDS:
                    frames = self._desired_frames[channel]
                    chunk_size = min(10, len(frames))
                    chunk = tuple(
                        frames[(frame_cursor[channel] + index) % len(frames)] for index in range(chunk_size)
                    )
                    await self._send_message(pulse_message(channel, chunk))
                    frame_cursor[channel] = (frame_cursor[channel] + chunk_size) % len(frames)
                    # Climax is a deliberate two-hit one-shot. Do not refill
                    # the queue until the engine changes away and a new edge
                    # selects it again.
                    last_wave_send[channel] = (
                        float("inf") if self._desired_wave_key[channel] == "climax" else now
                    )
            if now - last_heartbeat >= HEARTBEAT_SECONDS:
                await self._send_message("heartbeat")
                last_heartbeat = now

    def _emit(self, event: str, **payload) -> None:
        self.events.put(("dglab", {"event": event, **payload}))

