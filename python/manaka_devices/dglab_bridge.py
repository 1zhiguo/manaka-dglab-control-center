"""Embedded DG-LAB Socket server reused by the Ricca native application."""

from __future__ import annotations

import asyncio
import ipaddress
import json
import queue
import socket
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Iterable

import websockets
from . import audit
from .network import ipv4_interfaces


DEFAULT_PORT = 9999
HEARTBEAT_SECONDS = 25.0
WAVE_CHUNK_SECONDS = 0.10
WAVE_CLEAR_SETTLE_SECONDS = 0.15


def clamp_strength(value: float, hard_cap: int = 100) -> int:
    cap = max(0, min(100, int(hard_cap)))
    return max(0, min(cap, int(round(float(value)))))


def strength_message(channel: str, value: float, hard_cap: int = 100) -> str:
    code = "2" if str(channel).upper() == "B" else "1"
    return f"strength-{code}+2+{clamp_strength(value, hard_cap)}"


def pulse_message(channel: str, frames: Iterable[str]) -> str:
    clean: list[str] = []
    for frame in frames:
        value = str(frame).upper()
        if len(value) != 16 or any(char not in "0123456789ABCDEF" for char in value):
            raise ValueError("DG-LAB waveform frames must be 16 hexadecimal characters")
        clean.append(value)
    if not clean or len(clean) > 100:
        raise ValueError("DG-LAB waveform message must contain 1..100 frames")
    name = "B" if str(channel).upper() == "B" else "A"
    return f"pulse-{name}:{json.dumps(clean, separators=(',', ':'))}"


def discover_lan_ips() -> tuple[str, ...]:
    candidates: list[str] = []

    def add(address: str) -> None:
        try:
            parsed = ipaddress.ip_address(str(address))
        except ValueError:
            return
        if not isinstance(parsed, ipaddress.IPv4Address) or parsed.is_loopback or parsed.is_link_local:
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
    """Own a local Socket server and an internal controller connection."""

    def __init__(self, events: queue.Queue, *, port: int = DEFAULT_PORT, lan_ip: str = "") -> None:
        self.events = events
        self.requested_port = int(port)
        self.port = int(port)
        self.available_lan_interfaces = ipv4_interfaces()
        self.available_lan_ips = tuple(item["address"] for item in self.available_lan_interfaces) or discover_lan_ips() or ("127.0.0.1",)
        requested = str(lan_ip).strip()
        self.lan_ip = requested if requested in self.available_lan_ips else (
            self.available_lan_ips[0] if self.available_lan_ips else "127.0.0.1"
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
        self._paused = False
        self._pause_requested = False
        self._pause_epoch = 0
        self._pause_zero_task: asyncio.Task | None = None
        self._desired_strength = {"A": 0, "B": 0}
        self._desired_frames: dict[str, tuple[str, ...]] = {"A": (), "B": ()}
        self._desired_wave_key = {"A": "", "B": ""}
        self._hard_cap = 30
        self._desired_updated_at = 0.0
        self._resume_deferred = ""
        self._global_emergency_stop = threading.Event()

    def _emit(self, event: str, **payload) -> None:
        if event in {"ready", "connected", "disconnected", "error", "server_error", "output_timeout"}:
            audit.record("socket.state", state=event, connected=self.connected,
                         port=self.port)
        self.events.put(("dglab", {"event": event, **payload}))

    def _build_qr_url(self) -> str:
        return (
            "https://www.dungeon-lab.com/app-download.php#"
            f"DGLAB-SOCKET#ws://{self.lan_ip}:{self.port}/{self.controller_id}"
        )

    def snapshot(self) -> BridgeSnapshot:
        return BridgeSnapshot(self.server_ready, self.connected, self.controller_id,
                              self.target_id, self.qr_url, self.lan_ip, self.port)

    def set_lan_ip(self, address: str) -> bool:
        value = str(address).strip()
        if value not in self.available_lan_ips:
            return False
        self.lan_ip = value
        if self.server_ready and self.controller_id:
            self.qr_url = self._build_qr_url()
            self._emit("ready", qr_url=self.qr_url, lan_ip=value, port=self.port,
                       controller_id=self.controller_id)
        return True

    def refresh_lan_ips(self) -> None:
        self.available_lan_interfaces = ipv4_interfaces()
        self.available_lan_ips = tuple(item["address"] for item in self.available_lan_interfaces) or discover_lan_ips() or ("127.0.0.1",)

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._thread_main, name="DGLabSocketBridge", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self.emergency_stop()
        if self._loop is not None and self._stop_event is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._stop_event.set)
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def set_auto_enabled(self, enabled: bool) -> None:
        if self._loop is None or not self._loop.is_running():
            self._auto_enabled = False
            return
        self._loop.call_soon_threadsafe(self._set_auto_enabled_in_loop, bool(enabled))

    def set_paused(self, paused: bool) -> None:
        """Reversible master gate, including manual tests and queued output."""
        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._set_paused_in_loop, bool(paused))
        else:
            self._paused = self._pause_requested = bool(paused)

    def _set_paused_in_loop(self, paused: bool) -> None:
        if paused == self._pause_requested:
            return
        self._pause_requested = paused
        self._pause_epoch += 1
        if paused:
            self._paused = True
            self._generation += 1  # Invalidate any in-flight manual test.
            self._auto_enabled = False
            self._desired_strength = {"A": 0, "B": 0}
            self._desired_frames = {"A": (), "B": ()}
            self._desired_wave_key = {"A": "", "B": ""}
            self._desired_updated_at = 0.0
            self._pause_zero_task = asyncio.create_task(self._safe_zero_async())
        else:
            asyncio.create_task(self._release_pause(self._pause_epoch))

    async def _release_pause(self, epoch: int) -> None:
        # Finish both zeros/clears before allowing fresh output. Rapid
        # pause/resume must not let an old zero task erase a new waveform.
        task = self._pause_zero_task
        if task is not None:
            await task
        if epoch == self._pause_epoch and not self._pause_requested:
            self._paused = False

    def update_auto_outputs(self, strength_a: float, frames_a: Iterable[str], *,
                            wave_key_a: str, strength_b: float, frames_b: Iterable[str],
                            wave_key_b: str, hard_cap: int) -> None:
        clean_a = tuple(str(frame).upper() for frame in frames_a)
        clean_b = tuple(str(frame).upper() for frame in frames_b)
        if clean_a:
            pulse_message("A", clean_a[:100])
        if clean_b:
            pulse_message("B", clean_b[:100])
        if self._loop is not None and self._loop.is_running():
            cap = max(0, min(100, int(hard_cap)))
            self._loop.call_soon_threadsafe(
                self._set_desired_outputs_in_loop,
                clamp_strength(strength_a, cap), clean_a, str(wave_key_a),
                clamp_strength(strength_b, cap), clean_b, str(wave_key_b), cap,
            )

    def manual_test(self, strength: int, frames: Iterable[str], *, hard_cap: int,
                    channel: str = "A") -> bool:
        clean = tuple(str(frame).upper() for frame in frames)[:10]
        if not clean:
            return False
        clean_channel = str(channel).upper()
        if clean_channel not in {"A", "B"}:
            return False
        pulse_message(clean_channel, clean)
        if self._loop is None or not self._loop.is_running() or not self.connected or self._paused:
            return False
        safe = min(10, clamp_strength(strength, hard_cap))
        if safe <= 0:
            return False
        asyncio.run_coroutine_threadsafe(
            self._manual_test(clean_channel, safe, clean), self._loop
        )
        return True

    def emergency_stop(self) -> None:
        if self._loop is None or not self._loop.is_running():
            self._auto_enabled = False
            return
        self._loop.call_soon_threadsafe(self._request_emergency_in_loop)

    def latch_global_emergency_stop(self) -> None:
        # The native hotkey thread closes authorization synchronously, before
        # Qt can issue another frame or process the queued UI stop signal.
        self._global_emergency_stop.set()
        self.emergency_stop()

    def clear_global_emergency_stop(self) -> None:
        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._clear_global_emergency_in_loop)
        else:
            self._clear_global_emergency_in_loop()

    def _clear_global_emergency_in_loop(self) -> None:
        self._desired_updated_at = 0.0
        self._global_emergency_stop.clear()

    def _thread_main(self) -> None:
        try:
            asyncio.run(self._run())
        except Exception as error:
            self._emit("error", detail=f"Socket 服务异常：{error}")

    async def _run(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._pause_zero_task = None  # Never retain a task from a previous server loop.
        self._pause_epoch += 1
        self._paused = self._pause_requested
        self._auto_enabled = False
        self._desired_strength = {"A": 0, "B": 0}
        self._desired_frames = {"A": (), "B": ()}
        self._desired_wave_key = {"A": "", "B": ""}
        self._desired_updated_at = 0.0
        self._stop_event = asyncio.Event()
        try:
            self._server = await websockets.serve(self._server_handler, "0.0.0.0",
                                                  self.requested_port, ping_interval=20,
                                                  ping_timeout=20, max_size=1024 * 1024)
        except OSError as error:
            occupied = getattr(error, "winerror", None) == 10048 or error.errno in {98, 10048}
            detail = (f"端口 {self.requested_port} 已被占用。请关闭重复窗口，或点“连接不上？”查看占用进程。"
                      if occupied else f"无法监听端口 {self.requested_port}：{error}")
            self._emit("server_error", detail=detail)
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
        await websocket.send(json.dumps({"type": "bind", "clientId": connection_id,
                                         "targetId": "", "message": "targetId"}))
        try:
            async for raw in websocket:
                try:
                    packet = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    continue
                if packet.get("type") == "bind" and packet.get("message") == "DGLAB":
                    await self._handle_bind(websocket, connection_id, packet)
                elif packet.get("type") in {"msg", "heartbeat"}:
                    await self._forward_message(connection_id, packet)
        except websockets.ConnectionClosed:
            pass
        finally:
            peer = self._relations.pop(connection_id, None)
            self._clients.pop(connection_id, None)
            if peer:
                self._relations.pop(peer, None)
                if connection_id == self.target_id or peer == self.controller_id:
                    self._mark_disconnected()
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
            await websocket.send(json.dumps({"type": "bind", "clientId": controller_id,
                                             "targetId": phone_id, "message": "401"}))
            return
        self._relations[controller_id] = phone_id
        self._relations[phone_id] = controller_id
        response = json.dumps({"type": "bind", "clientId": controller_id,
                               "targetId": phone_id, "message": "200"})
        for client_id in (controller_id, phone_id):
            try:
                await self._clients[client_id].send(response)
            except websockets.ConnectionClosed:
                pass

    async def _forward_message(self, connection_id: str, packet: dict) -> None:
        first, second = str(packet.get("clientId", "")), str(packet.get("targetId", ""))
        peer = second if connection_id == first else first if connection_id == second else ""
        if not peer or self._relations.get(connection_id) != peer:
            if connection_id == self.controller_id:
                audit.record("socket.phone_forward", outcome="blocked", reason="binding-mismatch",
                             **audit.command_fields(str(packet.get("message", ""))))
            return
        target = self._clients.get(peer)
        if target is not None:
            try:
                await target.send(json.dumps(packet, separators=(",", ":")))
                if connection_id == self.controller_id:
                    audit.record("socket.phone_forward", outcome="written-to-phone-websocket",
                                 **audit.command_fields(str(packet.get("message", ""))))
            except websockets.ConnectionClosed:
                if connection_id == self.controller_id:
                    audit.record("socket.phone_forward", outcome="failed", reason="connection-closed",
                                 **audit.command_fields(str(packet.get("message", ""))))
            except Exception as error:
                if connection_id == self.controller_id:
                    audit.record("socket.phone_forward", outcome="failed", reason=type(error).__name__,
                                 **audit.command_fields(str(packet.get("message", ""))))
                raise
        elif connection_id == self.controller_id:
            audit.record("socket.phone_forward", outcome="blocked", reason="phone-websocket-missing",
                         **audit.command_fields(str(packet.get("message", ""))))

    async def _controller_client(self) -> None:
        try:
            async with websockets.connect(f"ws://127.0.0.1:{self.port}/", ping_interval=20,
                                          ping_timeout=20) as websocket:
                self._controller_ws = websocket
                hello = json.loads(await websocket.recv())
                self.controller_id = str(hello.get("clientId", ""))
                self.qr_url = self._build_qr_url()
                self._emit("ready", qr_url=self.qr_url, lan_ip=self.lan_ip,
                           port=self.port, controller_id=self.controller_id)
                async for raw in websocket:
                    packet = json.loads(raw)
                    kind = packet.get("type")
                    if kind == "bind" and str(packet.get("message")) == "200":
                        first, second = str(packet.get("clientId", "")), str(packet.get("targetId", ""))
                        self.target_id = second if first == self.controller_id else first
                        self.connected = True
                        # Never inherit a previous controller's strength or
                        # queued waveform when a phone binds to this session.
                        await self._safe_zero_async()
                        self._emit("connected", target_id=self.target_id)
                    elif kind == "break":
                        self._mark_disconnected()
                    elif kind == "msg":
                        feedback = str(packet.get("message", ""))
                        # A transport response is not a physical-stimulation acknowledgment.
                        if feedback.startswith("strength-") and len(feedback) < 80:
                            parts = feedback.removeprefix("strength-").split("+")
                            if len(parts) == 4 and all(part.isdigit() and len(part) <= 4 for part in parts):
                                audit.record("socket.feedback", kind="strength", values=[int(part) for part in parts])
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
        self._desired_updated_at = 0.0
        if was_connected:
            self._emit("disconnected")

    def _set_auto_enabled_in_loop(self, enabled: bool) -> None:
        next_enabled = bool(enabled and self.connected and not self._paused and not self._global_emergency_stop.is_set())
        if next_enabled and not self._auto_enabled:
            # Resume is asynchronous: a snapshot queued behind the resume
            # request can still be dropped while its zero/clear barrier runs.
            # Never arm from that empty/stale snapshot; wait for the next fresh
            # UI frame. Do not reset/extend the watchdog to hide this race.
            age = time.monotonic() - self._desired_updated_at
            zero_pending = self._pause_zero_task is not None and not self._pause_zero_task.done()
            if self._desired_updated_at <= 0 or not 0 <= age <= 0.5 or zero_pending:
                reason = "zero-clear-pending" if zero_pending else "awaiting-fresh-output"
                if reason != self._resume_deferred:
                    audit.record("socket.resume_deferred", reason=reason)
                    self._resume_deferred = reason
                return
        self._resume_deferred = ""
        if next_enabled == self._auto_enabled:
            return
        self._generation += 1
        self._auto_enabled = next_enabled
        if not self._auto_enabled:
            self._pause_zero_task = asyncio.create_task(self._safe_zero_async())

    def _set_desired_outputs_in_loop(self, strength_a: int, frames_a: tuple[str, ...],
                                     wave_a: str, strength_b: int, frames_b: tuple[str, ...],
                                     wave_b: str, hard_cap: int) -> None:
        if self._paused or self._global_emergency_stop.is_set():
            return  # Drop pre-pause/queued writes; resume requires fresh updates.
        self._desired_strength = {"A": strength_a, "B": strength_b}
        self._desired_frames = {"A": frames_a, "B": frames_b}
        self._desired_wave_key = {"A": wave_a, "B": wave_b}
        self._hard_cap = hard_cap
        self._desired_updated_at = time.monotonic()

    def _request_emergency_in_loop(self) -> None:
        self._generation += 1
        self._auto_enabled = False
        self._desired_strength = {"A": 0, "B": 0}
        self._desired_frames = {"A": (), "B": ()}
        self._desired_wave_key = {"A": "", "B": ""}
        self._desired_updated_at = 0.0
        self._pause_zero_task = asyncio.create_task(self._safe_zero_async())

    async def _send_message(self, message: str) -> bool:
        if (self._paused or self._global_emergency_stop.is_set()) and message not in {
                strength_message("A", 0), strength_message("B", 0), "clear-1", "clear-2", "heartbeat"}:
            audit.record("socket.controller_send", outcome="blocked", reason="bridge-paused",
                         **audit.command_fields(message))
            return False
        if not self.connected or self._controller_ws is None or not self.target_id:
            audit.record("socket.controller_send", outcome="blocked", reason="phone-not-bound",
                         **audit.command_fields(message))
            return False
        packet = {"type": "msg", "clientId": self.controller_id,
                  "targetId": self.target_id, "message": message}
        try:
            await self._controller_ws.send(json.dumps(packet, separators=(",", ":")))
            audit.record("socket.controller_send", outcome="written-to-controller-websocket",
                         **audit.command_fields(message))
            return True
        except websockets.ConnectionClosed:
            audit.record("socket.controller_send", outcome="failed", reason="connection-closed",
                         **audit.command_fields(message))
            self._mark_disconnected()
            return False
        except Exception as error:
            audit.record("socket.controller_send", outcome="failed", reason=type(error).__name__,
                         **audit.command_fields(message))
            raise

    async def _safe_zero_async(self) -> None:
        if not self.connected:
            return
        for message in (strength_message("A", 0), strength_message("B", 0), "clear-1", "clear-2"):
            await self._send_message(message)

    async def _manual_test(self, channel: str, strength: int,
                           frames: tuple[str, ...]) -> None:
        if self._paused:
            return
        self._generation += 1
        generation = self._generation
        self._auto_enabled = False
        await self._safe_zero_async()
        if generation != self._generation or not self.connected:
            return
        await self._send_message(
            strength_message(channel, strength, min(10, self._hard_cap))
        )
        await asyncio.sleep(0.15)
        if generation == self._generation and self.connected:
            await self._send_message(pulse_message(channel, frames))
            self._emit("test_started", strength=strength, channel=channel)
            await asyncio.sleep(1.0)
        if generation == self._generation:
            await self._safe_zero_async()
            self._emit("test_finished", channel=channel)

    async def _output_loop(self) -> None:
        last_strength: dict[str, int | None] = {"A": None, "B": None}
        last_wave = {"A": "", "B": ""}
        cursor = {"A": 0, "B": 0}
        last_send = {"A": 0.0, "B": 0.0}
        last_heartbeat = 0.0
        while True:
            await asyncio.sleep(0.02)
            # The Socket thread must also stop on a stalled Qt/telemetry loop.
            if self._auto_enabled and time.monotonic() - self._desired_updated_at > 0.5:
                audit.record("socket.watchdog_timeout",
                             desired_age_ms=round((time.monotonic() - self._desired_updated_at) * 1000, 1),
                             paused=self._paused, pause_requested=self._pause_requested,
                             requested=dict(self._desired_strength))
                self._request_emergency_in_loop()
                self._emit("output_timeout", detail="输出更新超时，已撤销授权并归零")
            if not self.connected or not self._auto_enabled:
                last_strength = {"A": None, "B": None}
                last_wave = {"A": "", "B": ""}
                cursor = {"A": 0, "B": 0}
                last_send = {"A": 0.0, "B": 0.0}
                continue
            now = time.monotonic()
            generation = self._generation
            for channel in ("A", "B"):
                if self._paused or not self._auto_enabled or generation != self._generation:
                    break
                clear = "clear-2" if channel == "B" else "clear-1"
                strength = clamp_strength(self._desired_strength[channel], self._hard_cap)
                if strength != last_strength[channel]:
                    await self._send_message(strength_message(channel, strength, self._hard_cap))
                    last_strength[channel] = strength
                if self._paused or not self._auto_enabled or generation != self._generation:
                    break
                frames = self._desired_frames[channel]
                if strength <= 0 or not frames:
                    if last_wave[channel]:
                        await self._send_message(clear)
                        last_wave[channel] = ""
                    continue
                if self._desired_wave_key[channel] != last_wave[channel]:
                    # Stream one 100 ms frame at a time.  On replacement the
                    # next frame takes over at the next boundary, so no old
                    # multi-frame queue can survive a stronger event.  Do not
                    # clear/sleep here: that used to swallow 100 ms pulses.
                    last_wave[channel] = self._desired_wave_key[channel]
                    cursor[channel] = 0
                if now - last_send[channel] >= WAVE_CHUNK_SECONDS:
                    size = 1
                    chunk = tuple(frames[(cursor[channel] + i) % len(frames)] for i in range(size))
                    await self._send_message(pulse_message(channel, chunk))
                    cursor[channel] = (cursor[channel] + size) % len(frames)
                    last_send[channel] = now
            if now - last_heartbeat >= HEARTBEAT_SECONDS:
                await self._send_message("heartbeat")
                last_heartbeat = now
