"""DG-LAB 4 local Socket adapter.

The embedded controller owns only the explicitly selected slot. No permanent
non-zero intensity tasks are used: temporary intensity expires after 300 ms,
and each waveform request contains one 100 ms frame. RPC completion is tracked
without awaiting a waveform task in the output loop.

Wire reference: dungeonlab-open/dglab-kit, README_CN.md (V4 protocol reference).
"""
from __future__ import annotations

import asyncio
import errno
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
import math
import queue
import threading
import time
from typing import Iterable
from urllib.parse import parse_qs, quote, urlsplit
import uuid

import websockets

from . import audit
from .dglab_bridge import DGLabBridge, clamp_strength
from manaka_dglab_bridge import clamp_strength as clamp_channel_strength
from manaka_wave_player import ChannelPlayer


V4_PORT = 9998
SUPPORTED_TYPES = frozenset({"COYOTE_030", "OVC_1"})
LEASE_MS = 300
FRAME_MS = 100
RPC_TIMEOUT = 2.0
MAX_PENDING = 128
SEND_TIMEOUT = .3
ZERO_TIMEOUT = 1.5


def protocol_strength(value: float, hard_cap: int, device_type: str) -> int:
    """OVC App tasks require ten-unit steps; never round intensity upward."""
    if device_type != "OVC_1":
        return clamp_channel_strength(value, hard_cap)
    try:
        requested, cap = float(value), float(hard_cap)
    except (TypeError, ValueError, OverflowError):
        return 0
    if not math.isfinite(requested) or not math.isfinite(cap):
        return 0
    return int(max(0.0, min(200.0, cap, requested)) // 10) * 10


def validate_v4_frames(frames: Iterable[str]) -> tuple[str, ...]:
    result = tuple(str(frame).upper() for frame in frames)
    if len(result) > 100:
        raise ValueError("V4 waveform may contain at most 100 frames")
    for value in result:
        if (not 2 <= len(value) <= 64 or len(value) % 2
                or any(char not in "0123456789ABCDEF" for char in value)):
            raise ValueError("V4 waveform frames must contain complete hexadecimal byte pairs")
    return result


@lru_cache(maxsize=128)
def validate_v4_stream(frames: tuple[str, ...]) -> None:
    for offset in range(0, len(frames), 100):
        validate_v4_frames(frames[offset:offset+100])


def _merge(target: dict, delta: dict) -> None:
    for key, value in delta.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge(target[key], value)
        else:
            target[key] = deepcopy(value)


def channel_block_reason(device: dict, channel: str) -> str:
    if device.get("type") == "COYOTE_020":
        return "unsupported-waveformat"
    if device.get("type") not in SUPPORTED_TYPES:
        return "unsupported-device"
    props, state = device.get("props", {}), device.get("slotState", {})
    if not isinstance(props, dict) or not isinstance(state, dict):
        return "missing-device-state"
    if (state.get("hasDevice") is False or props.get("connectState") == "disconnected"
            or not (state.get("hasDevice") is True or props.get("connectState") == "connected")):
        return "bluetooth-not-connected"
    channel_state = state.get("channel" + channel, {})
    if not isinstance(channel_state, dict):
        return "missing-device-state"
    if channel_state.get("isMuted") is True:
        return "channel-muted"
    status = props.get("channel" + channel + "Status")
    if device.get("type") == "OVC_1" and status is not True:
        return "accessory-not-inserted"
    if device.get("type") == "COYOTE_030" and type(status) is int and status in {3, 4}:
        return "channel-fault-or-blocked"
    return ""


class DGLabV4Bridge(DGLabBridge):
    """Bridge API compatible with V3; explicit V4 device selection is required."""

    protocol = "v4"

    def __init__(self, events: queue.Queue, *, port: int = V4_PORT, lan_ip: str = ""):
        super().__init__(events, port=port, lan_ip=lan_ip)
        self.app_connected = False
        self.selected_client_id = ""
        self.selected_slot_id = ""
        self.device_type = ""
        self._devices: dict[str, dict[str, dict]] = {}
        self._pending: dict[str, dict] = {}
        self._selection_epoch = 0
        self._selection_task: asyncio.Task | None = None
        self._selection_waiting_for_ready = False
        self._waiting_signature: tuple[str, str, str] | None = None
        self._readiness_failure_latched = False
        self._baseline_ready = False
        self._request_sequence = 0
        self._request_id_prefix = ""
        self._zero_locks: dict[tuple[str, str], asyncio.Lock] = {}
        self._zero_transactions: dict[tuple[str, str], asyncio.Task] = {}
        self._channel_zero_transactions: dict[tuple[str, str, int], asyncio.Task] = {}
        self._snapshot_lock = threading.Lock()
        self._public_devices: list[dict] = []
        self._last_device_state_signature = None
        self._last_discovery_signature = None
        self._channel_caps = {"A": 200, "B": 200}
        self._desired_loop = {"A": True, "B": True}
        self._desired_transition = {"A": "immediate", "B": "immediate"}
        self._sent_strengths = {"A": 0, "B": 0}
        self.playback_state = {key: ("", "stopped") for key in "AB"}

    @property
    def auto_enabled(self):
        return self._auto_enabled

    def channel_limit(self, channel):
        device = self._selected_device()
        maximum = device.get("slotState", {}).get("channel"+channel, {}).get("intensityMax", 200)
        return clamp_channel_strength(maximum)

    def channel_output(self, channel):
        return self._sent_strengths[channel] if self.connected and self.auto_enabled else 0

    def configure_limits(self, global_cap, cap_a, cap_b):
        values = tuple(clamp_channel_strength(v) for v in (global_cap, cap_a, cap_b))
        def apply():
            self._hard_cap = values[0]
            self._channel_caps = dict(A=min(values[0], values[1]), B=min(values[0], values[2]))
        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(apply)
        else:
            apply()

    def zero_output(self):
        # Keep the UI's enable intent; the transport must await a fresh frame
        # and the existing acknowledged zero barrier before it can resume.
        def clear_if_needed():
            if self._auto_enabled or any(self._desired_strength.values()) or any(self._desired_frames.values()):
                self._request_emergency_in_loop()
        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(clear_if_needed)

    def _playback(self, channel, key, state):
        value = (key.split("|", 1)[0], state)
        if self.playback_state[channel] != value:
            self.playback_state[channel] = value
            self._emit("playback", channel=channel, wave=value[0], state=state)

    def _build_qr_url(self) -> str:
        address = f"ws://{self.lan_ip}:{self.port}/?tid={self.controller_id}"
        return "https://dungeon-lab.cn/s/?v=1&action=socket&url=" + quote(address, safe="")

    def devices_snapshot(self) -> list[dict]:
        with self._snapshot_lock:
            return deepcopy(self._public_devices)

    def select_device(self, client_id: str, slot_id: str) -> bool:
        """Select once per connection; never restore a route from persisted IDs."""
        client_id, slot_id = str(client_id), str(slot_id)
        if self._loop is None or not self._loop.is_running():
            return False
        if not client_id and not slot_id:
            self._loop.call_soon_threadsafe(self._select_in_loop, "", "")
            return True
        if not any(item["clientId"] == client_id and item["slotId"] == slot_id
                   for item in self.devices_snapshot()):
            return False
        self._loop.call_soon_threadsafe(self._select_in_loop, client_id, slot_id)
        return True

    def _publish_devices(self) -> None:
        devices = []
        for client_id, slots in self._devices.items():
            for slot_id, raw in slots.items():
                item = deepcopy(raw)
                item.update(clientId=client_id, slotId=slot_id,
                            selected=(client_id == self.selected_client_id and slot_id == self.selected_slot_id),
                            channelAReason=channel_block_reason(raw, "A"),
                            channelBReason=channel_block_reason(raw, "B"))
                item["ready"] = not item["channelAReason"] or not item["channelBReason"]
                item["reason"] = "" if item["ready"] else item["channelAReason"]
                devices.append(item)
        with self._snapshot_lock:
            self._public_devices = devices
        # Log discovery before any selection exists, without names, QR URLs,
        # waveform payloads or unrelated APP data. State transitions only.
        discovery = []
        for item in devices:
            props, state = item.get("props") or {}, item.get("slotState") or {}
            discovery.append({"app_client_id": item["clientId"], "slot_id": item["slotId"],
                "device_type": item.get("type"),
                "has_device": state.get("hasDevice") if isinstance(state, dict) else None,
                "connect_state": props.get("connectState") if isinstance(props, dict) else None,
                "channel_a_reason": item["channelAReason"], "channel_b_reason": item["channelBReason"]})
        signature = json.dumps(discovery, sort_keys=True, ensure_ascii=False)
        if signature != self._last_discovery_signature:
            self._last_discovery_signature = signature
            audit.record("socket.v4_discovery", role=getattr(self, "role", "single"),
                         app_connected=self.app_connected, count=len(discovery), devices=discovery)
        self._emit("devices", devices=devices, app_connected=self.app_connected,
                   selected_client_id=self.selected_client_id,
                   selected_slot_id=self.selected_slot_id, device_type=self.device_type)

    def _discard_outputs(self) -> None:
        self._generation += 1
        self._auto_enabled = False
        self._desired_strength = {"A": 0, "B": 0}
        self._desired_frames = {"A": (), "B": ()}
        self._desired_wave_key = {"A": "", "B": ""}
        self._desired_updated_at = 0.0
        self._sent_strengths = {"A": 0, "B": 0}
        self.playback_state = {key: ("", "stopped") for key in "AB"}

    def _route_zero_pending(self, client_id: str = "", slot_id: str = "") -> bool:
        route = (client_id or self.selected_client_id, slot_id or self.selected_slot_id)
        task = self._zero_transactions.get(route)
        return task is not None and not task.done()

    def _set_auto_enabled_in_loop(self, enabled: bool) -> None:
        if enabled and self._route_zero_pending():
            return  # A canceled caller must not release an older clear barrier.
        super()._set_auto_enabled_in_loop(enabled)

    def _channel_zero_pending(self, client_id: str, slot_id: str, channel: int) -> bool:
        task = self._channel_zero_transactions.get((client_id, slot_id, channel))
        return task is not None and not task.done()

    def _select_in_loop(self, client_id: str, slot_id: str) -> None:
        old = (self.selected_client_id, self.selected_slot_id)
        self._selection_epoch += 1
        self._discard_outputs()
        self.connected = False
        self._baseline_ready = False
        self._selection_waiting_for_ready = bool(client_id and slot_id)
        self._waiting_signature = None
        self._readiness_failure_latched = False
        self.selected_client_id, self.selected_slot_id = client_id, slot_id
        device = self._devices.get(client_id, {}).get(slot_id, {})
        self.device_type = str(device.get("type", ""))
        self.target_id = client_id
        if self._selection_task and not self._selection_task.done():
            self._selection_task.cancel()
        self._launch_selection(self._selection_epoch, old)
        self._publish_devices()

    def _launch_selection(self, epoch: int, old: tuple[str, str]) -> None:
        task = asyncio.create_task(self._prepare_selection(epoch, old))
        self._selection_task = task
        def finished(done):
            if self._selection_task is done and not done.cancelled():
                error = done.exception()
                if error is not None:
                    self.connected = self._baseline_ready = False
                    self._selection_waiting_for_ready = False
                    self._readiness_failure_latched = True
                    self._waiting_signature = None
                    self._audit_readiness("unexpected-selection-failure")
                    self._emit("error", detail=f"V4 设备归零确认失败：{type(error).__name__}")
                else:
                    self._check_selected()
        task.add_done_callback(finished)

    def _audit_readiness(self, phase: str) -> None:
        device = self._selected_device()
        props = device.get("props") if isinstance(device.get("props"), dict) else {}
        state = device.get("slotState") if isinstance(device.get("slotState"), dict) else {}
        audit.record("socket.v4_readiness", phase=phase,
                     role=getattr(self, "role", "single"),
                     app_client_id=self.selected_client_id, slot_id=self.selected_slot_id,
                     device_type=self.device_type, has_device=state.get("hasDevice"),
                     connect_state=props.get("connectState"),
                     channel_a_reason=channel_block_reason(device, "A"),
                     channel_b_reason=channel_block_reason(device, "B"),
                     channel_a_muted=(state.get("channelA") or {}).get("isMuted") if isinstance(state.get("channelA"), dict) else None,
                     channel_b_muted=(state.get("channelB") or {}).get("isMuted") if isinstance(state.get("channelB"), dict) else None,
                     intensity_a=props.get("intensityA"), intensity_b=props.get("intensityB"),
                     baseline_ready=self._baseline_ready)

    async def _prepare_selection(self, epoch: int, old: tuple[str, str]) -> None:
        client_id, slot_id = self.selected_client_id, self.selected_slot_id
        try:
            if old[0] and old[1] and old != (client_id, slot_id):
                await self._zero_route(*old)
            device = self._devices.get(client_id, {}).get(slot_id)
            if not device or all(channel_block_reason(device, channel) for channel in ("A", "B")):
                self._audit_readiness("awaiting-device-state")
                return
            # Await the reset/clear acknowledgments before publishing output
            # readiness. Responses are task-end notifications, not queue acks.
            await self._zero_route(client_id, slot_id, wait=True)
            if epoch != self._selection_epoch:
                return
            device = self._devices.get(client_id, {}).get(slot_id)
            if not device or all(channel_block_reason(device, channel) for channel in ("A", "B")):
                self._audit_readiness("state-blocked-after-zero")
                return
            self._baseline_ready = self.connected = True
            self._selection_waiting_for_ready = False
            self._waiting_signature = None
            self._discard_outputs()  # A fresh backend update is still required.
            self._audit_readiness("ready")
            self._emit("connected", target_id=client_id, slot_id=slot_id, device_type=self.device_type)
            self._publish_devices()
        except asyncio.CancelledError:
            raise
        except (TimeoutError, ConnectionError, ValueError) as error:
            if epoch == self._selection_epoch:
                self.connected = self._baseline_ready = False
                self._selection_waiting_for_ready = False
                self._readiness_failure_latched = True
                self._waiting_signature = None
                self._audit_readiness("zero-confirmation-failed")
                self._emit("error", detail=f"V4 设备归零确认失败：{type(error).__name__}")

    def _selected_device(self) -> dict:
        return self._devices.get(self.selected_client_id, {}).get(self.selected_slot_id, {})

    def _wait_for_selected_coyote(self, reason: str) -> None:
        """Keep an existing electrical slot selected, but revoke its output.

        A transient Bluetooth/mute tick isn't a catalog removal. Only a fresh,
        acknowledged baseline can make this route ready again; backend still
        requires explicit user resume. Stable waiting ticks do no new work.
        """
        signature = (self.selected_client_id, self.selected_slot_id, reason)
        preparing = self._selection_task is not None and not self._selection_task.done()
        if self._waiting_signature is None or preparing:
            had_output = self.connected or self._baseline_ready or self._auto_enabled
            self._selection_epoch += 1
            if preparing:
                self._selection_task.cancel()
            # Detach the canceled waiter, not its shielded zero transaction.
            # A valid tick can now queue a fresh baseline without an old task
            # publishing readiness for the previous epoch.
            self._selection_task = None
            self._discard_outputs()
            self.connected = self._baseline_ready = False
            self._selection_waiting_for_ready = True
            if had_output:
                asyncio.create_task(self._safe_zero_async())
        if self._waiting_signature != signature:
            self._waiting_signature = signature
            self._audit_readiness("waiting-device-state")
            self._emit("waiting", reason=reason, target_id=self.selected_client_id,
                       slot_id=self.selected_slot_id, device_type=self.device_type)

    def _check_selected(self) -> None:
        if not self.selected_slot_id:
            return
        device = self._selected_device()
        props = device.get("props") if isinstance(device.get("props"), dict) else {}
        state = device.get("slotState") if isinstance(device.get("slotState"), dict) else {}
        signature = (self.selected_client_id, self.selected_slot_id, self.device_type,
                     state.get("hasDevice"), props.get("connectState"),
                     props.get("intensityA"), props.get("intensityB"),
                     channel_block_reason(device, "A"), channel_block_reason(device, "B"))
        if signature != self._last_device_state_signature:
            self._last_device_state_signature = signature
            self._audit_readiness("device-state-update")
        reasons = {channel: channel_block_reason(device, channel) for channel in ("A", "B")}
        if (not device or device.get("type") != self.device_type
                or (self.device_type == "COYOTE_030" and self.selected_client_id not in self._clients)):
            self._lose_selection("selected-device-disconnected")
        elif self.device_type == "COYOTE_030" and all(reasons.values()):
            if not self._readiness_failure_latched:
                reason = (reasons["A"] if reasons["A"] == reasons["B"]
                          else "all-channels-blocked")
                self._wait_for_selected_coyote(reason)
        elif reasons["A"] == "bluetooth-not-connected":
            # OVC retains the original fail-closed/deselect behavior.
            self._lose_selection("selected-device-disconnected")
        elif self.connected and all(channel_block_reason(device, channel) for channel in ("A", "B")):
            # Both channels are inhibited. Keep selection, but stop now;
            # unmuting requires selecting the device again, not an auto-resume.
            self.connected = self._baseline_ready = False
            self._selection_waiting_for_ready = False
            self._discard_outputs()
            asyncio.create_task(self._safe_zero_async())
            self._emit("disconnected", reason="all-channels-blocked")
        elif (self._selection_waiting_for_ready and not self.connected
              and any(not channel_block_reason(device, channel) for channel in ("A", "B"))
              and (self._selection_task is None or self._selection_task.done())):
            # Selection is explicit, but an APP may announce the slot before
            # its first accessory/Bluetooth state tick. Prepare it once that
            # state arrives; this does NOT authorize non-zero output.
            self._launch_selection(self._selection_epoch,
                                   (self.selected_client_id, self.selected_slot_id))

    def _lose_selection(self, reason: str) -> None:
        old = (self.selected_client_id, self.selected_slot_id)
        old_type = self.device_type
        was_connected = self.connected
        self._selection_epoch += 1
        if self._selection_task and not self._selection_task.done():
            self._selection_task.cancel()
        self._discard_outputs()
        self.connected = self._baseline_ready = False
        self._selection_waiting_for_ready = False
        self._waiting_signature = None
        self._readiness_failure_latched = False
        self.selected_client_id = self.selected_slot_id = self.device_type = self.target_id = ""
        if old[0] in self._clients:
            asyncio.create_task(self._zero_route(*old))
        if was_connected or old[1]:
            self._emit("disconnected", reason=reason, target_id=old[0], slot_id=old[1], device_type=old_type)

    async def _listen(self) -> bool:
        """Prefer the configured port, then let the OS choose an available one.

        Windows can reserve 9998 even when no process is listening on it.
        Both routes and the QR must use the actual bound socket's port.
        """
        self.server_ready = False
        self.qr_url = ""
        self._server = None
        ports = (self.requested_port, 0) if self.requested_port else (0,)
        for port in ports:
            try:
                self._server = await websockets.serve(
                    self._server_handler, "0.0.0.0", port, ping_interval=20,
                    ping_timeout=20, close_timeout=.5, max_size=1024 * 1024)
            except OSError as error:
                retryable = (error.errno in {errno.EADDRINUSE, errno.EACCES, 10013, 10048}
                             or getattr(error, "winerror", None) in {10013, 10048})
                if port and retryable:
                    continue
                self._emit("server_error", detail=f"无法启动 V4 监听服务（首选端口 {self.requested_port}，尝试端口 {port}）：{error}")
                return False
            self.port = int(self._server.sockets[0].getsockname()[1])
            return True
        return False

    async def _run(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._stop_event = asyncio.Event()
        self._pause_zero_task = None
        self._paused = self._pause_requested
        self._discard_outputs()
        self._devices.clear()
        self._clients.clear()
        self._pending.clear()
        self._zero_locks.clear()
        self._zero_transactions.clear()
        self._channel_zero_transactions.clear()
        self._waiting_signature = None
        self._readiness_failure_latched = False
        self.selected_client_id = self.selected_slot_id = self.device_type = self.target_id = ""
        self.connected = self.app_connected = self._baseline_ready = False
        self.controller_id = str(uuid.uuid4())
        if not await self._listen():
            return
        self.server_ready = True
        self.qr_url = self._build_qr_url()
        self._emit("ready", qr_url=self.qr_url, lan_ip=self.lan_ip, port=self.port,
                   controller_id=self.controller_id, protocol="v4")
        output = asyncio.create_task(self._output_loop())
        try:
            await self._stop_event.wait()
        finally:
            self._discard_outputs()
            await self._safe_zero_async()
            if self._selection_task and not self._selection_task.done():
                self._selection_task.cancel()
                await asyncio.gather(self._selection_task, return_exceptions=True)
            output.cancel()
            await asyncio.gather(output, return_exceptions=True)
            self._server.close()
            await self._server.wait_closed()
            zeros = [*self._zero_transactions.values(), *self._channel_zero_transactions.values()]
            if zeros:
                await asyncio.gather(*zeros, return_exceptions=True)
            self.server_ready = False
            self.qr_url = ""
            self._mark_disconnected()

    async def _server_handler(self, websocket) -> None:
        request = getattr(websocket, "request", None)
        path = getattr(request, "path", getattr(websocket, "path", "/"))
        tid = parse_qs(urlsplit(path).query).get("tid", [""])[0]
        if tid != self.controller_id:
            await websocket.send(json.dumps({"type": "error", "message": "controller_not_found"}))
            await websocket.close(code=4001, reason="controller_not_found")
            return
        client_id = str(uuid.uuid4())
        self._clients[client_id] = websocket
        self._devices[client_id] = {}
        self.app_connected = True
        heartbeat = None
        try:
            await asyncio.wait_for(websocket.send(json.dumps({"type": "hello", "clientId": client_id})), SEND_TIMEOUT)
            await asyncio.wait_for(websocket.send(json.dumps({"type": "controller_attached", "clientId": self.controller_id})), SEND_TIMEOUT)
            self._emit("app_connected", client_id=client_id, protocol="v4")
            await self._rpc("devices.get", None, client_id=client_id)
            self._publish_devices()
            heartbeat = asyncio.create_task(self._heartbeat(websocket))
            async for raw in websocket:
                try:
                    packet = json.loads(raw)
                except (ValueError, TypeError):
                    continue
                if not isinstance(packet, dict):
                    continue
                if packet.get("type") == "ping":
                    await websocket.send(json.dumps({"type": "pong", "ts": round(time.time() * 1000)}))
                elif packet.get("type") == "message" and isinstance(packet.get("data"), dict):
                    self._handle_app_data(client_id, packet["data"])
        except (websockets.ConnectionClosed, TimeoutError, ConnectionError):
            pass
        finally:
            if heartbeat:
                heartbeat.cancel()
                await asyncio.gather(heartbeat, return_exceptions=True)
            self._clients.pop(client_id, None)
            self._devices.pop(client_id, None)
            self.app_connected = bool(self._clients)
            if self.selected_client_id == client_id:
                self._lose_selection("app-disconnected")
            for req_id, pending in list(self._pending.items()):
                if pending["client_id"] == client_id:
                    self._finish_pending(req_id, error=ConnectionError("APP disconnected"))
            self._publish_devices()

    async def _heartbeat(self, websocket) -> None:
        while True:
            await asyncio.sleep(30)
            await asyncio.wait_for(websocket.send('{"type":"heartbeat"}'), SEND_TIMEOUT)

    def _handle_app_data(self, client_id: str, data: dict) -> None:
        if data.get("t") == "resp":
            req_id = data.get("reqId")
            pending = self._pending.get(req_id) if isinstance(req_id, str) else None
            if not pending or pending["client_id"] != client_id:
                return
            error = data.get("error")
            if error is not None:
                self._finish_pending(req_id, error=ValueError(str(error)[:100]))
                if pending["method"] == "device.op" and not pending["safety"]:
                    self._request_emergency_in_loop()
                    self._emit("error", detail=f"V4 APP 拒绝输出任务：{str(error)[:100]}")
                return
            result = data.get("result")
            if pending["method"] == "device.op" and not pending["safety"]:
                if (not isinstance(result, dict)
                        or result.get("reason") not in {"completed", "cleared", "replaced"}
                        or result.get("type") != pending.get("action_type")
                        or result.get("slotId", pending.get("slot_id")) != pending.get("slot_id")
                        or result.get("channel", pending.get("channel")) != pending.get("channel")):
                    self._finish_pending(req_id, error=ValueError("Output task cancelled or invalid completion"))
                    stale_coyote_cancel = (
                        self.device_type == "COYOTE_030" and isinstance(result, dict)
                        and result.get("reason") == "cancelled"
                        and result.get("type") == pending.get("action_type")
                        and result.get("slotId", pending.get("slot_id")) == pending.get("slot_id")
                        and result.get("channel", pending.get("channel")) == pending.get("channel")
                        and pending.get("slot_id") == self.selected_slot_id
                        and pending.get("client_id") == self.selected_client_id
                        and type(pending.get("generation")) is int
                        and pending["generation"] < self._generation)
                    if not stale_coyote_cancel:
                        self._lose_selection("output-task-cancelled-or-invalid")
                    # A Bluetooth/mute wait revokes the previous generation.
                    # Its delayed cancellation must not erase a retained (or
                    # freshly re-baselined) electrical selection.
                    self._publish_devices()
                    return
            if pending["method"] == "devices.get" and isinstance(result, dict):
                self._replace_devices(client_id, result.get("devices"))
            self._finish_pending(req_id, result=result)
            return
        if data.get("t") != "ev":
            return
        event = data.get("ev")
        slots = self._devices.setdefault(client_id, {})
        if event == "devices.snapshot":
            self._replace_devices(client_id, data.get("devices"))
            return
        if event == "devices.patch":
            for slot_id in data.get("removed", []) if isinstance(data.get("removed"), list) else []:
                if isinstance(slot_id, str):
                    slots.pop(slot_id, None)
            for item in data.get("added", []) if isinstance(data.get("added"), list) else []:
                if isinstance(item, dict) and isinstance(item.get("slotId"), str):
                    slots[item["slotId"]] = deepcopy(item)
        elif event == "slots.patch":
            for item in data.get("slots", []) if isinstance(data.get("slots"), list) else []:
                if isinstance(item, dict) and isinstance(item.get("slotId"), str) and item["slotId"] in slots:
                    _merge(slots[item["slotId"]], item)
        elif event == "custom.action":
            if type(data.get("action")) is int and 0 <= data["action"] <= 9:
                self._emit("feedback", message=f"feedback-{data['action']}")
            return
        else:
            return
        self._check_selected()
        self._publish_devices()

    def _replace_devices(self, client_id: str, devices) -> None:
        if not isinstance(devices, list):
            return
        self._devices[client_id] = {item["slotId"]: deepcopy(item) for item in devices[:64]
                                   if isinstance(item, dict) and isinstance(item.get("slotId"), str)}
        self._check_selected()
        self._publish_devices()

    def _finish_pending(self, req_id: str, *, result=None, error: Exception | None = None) -> None:
        pending = self._pending.pop(req_id, None)
        if pending is None:
            return
        audit.record("socket.v4_response", request_id=req_id, method=pending["method"],
                     outcome="error" if error else "task-finished",
                     reason=str(error) if error else (result.get("reason") if isinstance(result, dict) else None),
                     role=getattr(self, "role", "single"),
                     app_client_id=pending.get("client_id"), slot_id=pending.get("slot_id"),
                     result_type=result.get("type") if isinstance(result, dict) else type(result).__name__,
                     result_channel=result.get("channel") if isinstance(result, dict) else None,
                     result_slot_id=result.get("slotId") if isinstance(result, dict) else None)
        future = pending.get("future")
        if future is not None and not future.done():
            if error:
                future.set_exception(error)
            else:
                future.set_result(result)

    async def _rpc(self, method: str, data: dict | None, *, client_id: str = "",
                   safety: bool = False, wait: bool = False):
        client_id = client_id or self.selected_client_id
        websocket = self._clients.get(client_id)
        if websocket is None:
            raise ConnectionError("APP not connected")
        is_output = method == "device.op" and not safety
        if is_output and (not self.connected or not self._baseline_ready or self._paused
                          or self._global_emergency_stop.is_set() or client_id != self.selected_client_id
                          or not data or data.get("s") != self.selected_slot_id
                          or self._route_zero_pending(client_id, data.get("s", ""))
                          or self._channel_zero_pending(client_id, data.get("s", ""), data.get("c", 0))
                          or channel_block_reason(self._selected_device(), "B" if data.get("c") == 1 else "A")):
            audit.record("socket.v4_send", outcome="blocked", reason="output-gate", method=method,
                         role=getattr(self, "role", "single"), app_client_id=client_id,
                         slot_id=data.get("s") if data else None,
                         channel=data.get("c") if data else None,
                         connected=self.connected, baseline_ready=self._baseline_ready,
                         paused=self._paused, emergency_stop=self._global_emergency_stop.is_set())
            return False
        if len(self._pending) >= MAX_PENDING and not safety:
            raise ConnectionError("V4 pending request limit")
        self._request_sequence += 1
        req_id = f"{self._request_id_prefix}r{self._request_sequence}"
        packet = {"t": "req", "reqId": req_id, "m": method}
        if data is not None:
            packet["data"] = data
        future = asyncio.get_running_loop().create_future() if wait else None
        # Safety writes are never blocked by missing task completions. At the
        # bound, fire-and-forget safety requests are still sent but not cached.
        if len(self._pending) < MAX_PENDING or wait:
            self._pending[req_id] = {"client_id": client_id, "method": method, "safety": safety,
                                     "deadline": time.monotonic() + RPC_TIMEOUT, "future": future,
                                     "action_type": data.get("t") if data else None,
                                     "generation": self._generation,
                                     "slot_id": data.get("s") if data else None,
                                     "channel": data.get("c") if data else None}
        fields = {"request_id": req_id, "method": method, "protocol": "v4",
                  "role": getattr(self, "role", "single"),
                  "app_client_id": client_id, "slot_id": data.get("s") if data else None}
        if data:
            fields.update(action_type=data.get("t"), channel=data.get("c"), duration_ms=data.get("d"))
            if data.get("t") in {4, 7}:
                fields["strength"] = data.get("v")
            elif data.get("t") == 0:
                fields["frame_count"] = len(data.get("v", []))
                fields["sha256"] = hashlib.sha256(json.dumps(data.get("v")).encode()).hexdigest()
        generation = self._generation

        async def write_current_request():
            # wait_for schedules its coroutine in another task. Re-check at
            # the actual write, not only before scheduling: Stop/selection can
            # invalidate a request during that scheduling gap.
            if is_output and (generation != self._generation or not self._auto_enabled
                              or self._global_emergency_stop.is_set() or self._paused
                              or not self.connected or not self._baseline_ready
                              or client_id != self.selected_client_id
                              or data.get("s") != self.selected_slot_id):
                return False
            await websocket.send(json.dumps({"type": "message", "data": packet}, separators=(",", ":")))
            return True

        try:
            written = await asyncio.wait_for(write_current_request(), SEND_TIMEOUT)
            if not written:
                self._pending.pop(req_id, None)
                if future is not None and not future.done():
                    future.cancel()
                return False
            audit.record("socket.v4_send", outcome="written-to-phone-websocket", **fields)
            if wait:
                return await asyncio.wait_for(future, RPC_TIMEOUT)
            return True
        except BaseException as error:
            self._pending.pop(req_id, None)
            if future is not None and not future.done():
                future.cancel()
            audit.record("socket.v4_send", outcome="failed", reason=type(error).__name__, **fields)
            if isinstance(error, (TimeoutError, websockets.ConnectionClosed)):
                self._discard_outputs()
                self.connected = self._baseline_ready = False
                self._emit("disconnected", reason="app-write-or-response-timeout")
                self._close_for_route_error(client_id, "output_link_timeout")
            raise

    def _close_for_route_error(self, client_id: str, reason: str) -> None:
        self._readiness_failure_latched = True
        self._selection_waiting_for_ready = False
        self._waiting_signature = None
        websocket = self._clients.get(client_id)
        if websocket is not None:
            asyncio.create_task(websocket.close(code=1011, reason=reason))

    async def _zero_route(self, client_id: str, slot_id: str, *, wait: bool = False) -> None:
        if not client_id or not slot_id or client_id not in self._clients:
            return
        route = (client_id, slot_id)
        task = self._zero_transactions.get(route)
        if task is None or task.done():
            task = asyncio.create_task(self._zero_transaction(client_id, slot_id))
            self._zero_transactions[route] = task
            def finished(done):
                if self._zero_transactions.get(route) is done:
                    self._zero_transactions.pop(route, None)
                if not done.cancelled():
                    done.exception()  # A canceled selection may have no waiter.
            task.add_done_callback(finished)
        try:
            # Rapid selection may cancel its waiter, never the transaction.
            # Coalescing also prevents same-tick im=true zero requests from
            # replacing one another while a baseline awaits completion.
            await asyncio.shield(task)
        except (websockets.ConnectionClosed, ConnectionError, TimeoutError, ValueError):
            if wait:
                raise ConnectionError("APP disconnected while zeroing")

    async def _zero_transaction(self, client_id: str, slot_id: str) -> None:
        route = (client_id, slot_id)
        lock = self._zero_locks.setdefault(route, asyncio.Lock())
        try:
            async with asyncio.timeout(ZERO_TIMEOUT):
                async with lock:
                    # Send both channel zeros immediately; await both task
                    # completions before enqueueing clear or final zeros.
                    await self._zero_channels(client_id, slot_id, (0, 1))
                    result = await self._rpc("device.op.clear", {"s": slot_id},
                                             client_id=client_id, safety=True, wait=True)
                    if not isinstance(result, dict):
                        raise ValueError("Invalid clear acknowledgment")
                    await self._zero_channels(client_id, slot_id, (0, 1))
        except (websockets.ConnectionClosed, ConnectionError, TimeoutError, ValueError):
            if client_id == self.selected_client_id:
                self._discard_outputs()
                self.connected = self._baseline_ready = False
            self._close_for_route_error(client_id, "zero_barrier_failed")
            raise

    async def _zero_channels(self, client_id: str, slot_id: str, channels: tuple[int, ...]) -> None:
        results = await asyncio.gather(*[
            self._rpc("device.op", {"s": slot_id, "t": 7, "c": channel, "p": 1, "v": 0, "im": True},
                      client_id=client_id, safety=True, wait=True) for channel in channels
        ], return_exceptions=True)
        for channel, result in zip(channels, results):
            if isinstance(result, BaseException):
                raise result
            self._validate_zero_result(result, slot_id, channel)

    def _start_channel_zero(self, client_id: str, slot_id: str, channel: int) -> None:
        route = (client_id, slot_id, channel)
        if self._channel_zero_pending(*route):
            return
        task = asyncio.create_task(self._zero_channel(client_id, slot_id, channel))
        self._channel_zero_transactions[route] = task
        def finished(done):
            if self._channel_zero_transactions.get(route) is done:
                self._channel_zero_transactions.pop(route, None)
            if not done.cancelled():
                done.exception()
        task.add_done_callback(finished)

    async def _zero_channel(self, client_id: str, slot_id: str, channel: int) -> None:
        lock = self._zero_locks.setdefault((client_id, slot_id), asyncio.Lock())
        try:
            async with asyncio.timeout(ZERO_TIMEOUT):
                async with lock:
                    await self._zero_channels(client_id, slot_id, (channel,))
                    result = await self._rpc("device.op.clear", {"s": slot_id, "c": channel},
                                             client_id=client_id, safety=True, wait=True)
                    if not isinstance(result, dict):
                        raise ValueError("Invalid clear acknowledgment")
                    await self._zero_channels(client_id, slot_id, (channel,))
        except (websockets.ConnectionClosed, ConnectionError, TimeoutError, ValueError):
            if client_id == self.selected_client_id:
                self._discard_outputs()
                self.connected = self._baseline_ready = False
            self._close_for_route_error(client_id, "channel_zero_failed")
            raise

    @staticmethod
    def _validate_zero_result(result, slot_id: str, channel: int) -> None:
        if (not isinstance(result, dict) or result.get("type") != 7
                or result.get("reason") != "completed"
                or result.get("slotId", slot_id) != slot_id
                or result.get("channel", channel) != channel):
            raise ValueError("V4 zero task did not complete for the selected route")

    async def _safe_zero_async(self) -> None:
        await self._zero_route(self.selected_client_id, self.selected_slot_id)

    def _mark_disconnected(self) -> None:
        self._discard_outputs()
        self.connected = self.app_connected = self._baseline_ready = False
        self._selection_waiting_for_ready = False
        self._waiting_signature = None
        self._readiness_failure_latched = False
        self.target_id = self.selected_client_id = self.selected_slot_id = self.device_type = ""

    def update_auto_outputs(self, strength_a: float, frames_a: Iterable[str], *,
                            wave_key_a: str, strength_b: float, frames_b: Iterable[str],
                            wave_key_b: str, hard_cap: int, received_at=None,
                            cap_a=None, cap_b=None, loop_a=True, loop_b=True,
                            transition_a="immediate", transition_b="immediate") -> None:
        a, b = tuple(frames_a), tuple(frames_b)
        for frames in (a, b):
            validate_v4_stream(frames)
        received_at = time.monotonic() if received_at is None else float(received_at)
        if not math.isfinite(received_at) or not 0 <= time.monotonic()-received_at < .5:
            return
        if self._loop is not None and self._loop.is_running():
            cap = clamp_channel_strength(hard_cap)
            caps = {"A": min(cap, clamp_channel_strength(cap if cap_a is None else cap_a)),
                    "B": min(cap, clamp_channel_strength(cap if cap_b is None else cap_b))}
            generation = self._generation
            def apply():
                if generation != self._generation or not 0 <= time.monotonic()-received_at < .5:
                    return
                self._channel_caps = caps
                self._desired_loop = dict(A=bool(loop_a), B=bool(loop_b))
                self._desired_transition = dict(A=transition_a, B=transition_b)
                self._set_desired_outputs_in_loop(
                    protocol_strength(strength_a, caps["A"], self.device_type), a, str(wave_key_a),
                    protocol_strength(strength_b, caps["B"], self.device_type), b, str(wave_key_b), cap)
                # Queueing in the GUI/Socket loop cannot renew old telemetry.
                self._desired_updated_at = min(self._desired_updated_at, received_at)
            self._loop.call_soon_threadsafe(apply)

    def manual_test(self, strength: int, frames: Iterable[str], *, hard_cap: int, channel: str = "A") -> bool:
        # Device tests are deliberately unavailable in V4. The user exercises
        # game-driven output after explicit selection with their chosen cap.
        return False

    def _channel_strength(self, channel: str) -> int:
        device = self._selected_device()
        if channel_block_reason(device, channel):
            return 0
        cap = min(self._hard_cap, self._channel_caps[channel])
        maximum = device.get("slotState", {}).get("channel" + channel, {}).get("intensityMax")
        if type(maximum) in {int, float} and math.isfinite(maximum):
            cap = min(cap, max(0, int(maximum)))
        return protocol_strength(self._desired_strength[channel], cap, self.device_type)

    async def _output_loop(self) -> None:
        players = {key: ChannelPlayer(lookahead=.1, settle=0) for key in "AB"}
        last_wave = {"A": "", "B": ""}
        cursor = {"A": 0, "B": 0}
        active = {"A": False, "B": False}
        last_send = {"A": 0.0, "B": 0.0}
        last_generation = -1
        while True:
            await asyncio.sleep(.02)
            now = time.monotonic()
            for req_id, pending in list(self._pending.items()):
                if pending["deadline"] < now:
                    self._finish_pending(req_id, error=TimeoutError("V4 response timed out"))
                    if pending["method"] == "device.op" and not pending["safety"] and self._auto_enabled:
                        self._request_emergency_in_loop()
                        self._emit("output_timeout", reason="response-timeout", detail="V4 APP 输出任务确认超时，已归零")
            if self._auto_enabled and now - self._desired_updated_at > .5:
                producer_age_ms = round((now-self._desired_updated_at)*1000)
                self._request_emergency_in_loop()
                self._emit("output_timeout", reason="producer-stale", producer_age_ms=producer_age_ms, producer_stalled_at=now,
                           detail="输出更新超时，已撤销授权并归零")
            if self._generation != last_generation:
                last_generation = self._generation
                last_wave = {"A": "", "B": ""}
                cursor = {"A": 0, "B": 0}
                last_send = {"A": 0.0, "B": 0.0}
                active = {"A": False, "B": False}
                players = {key: ChannelPlayer(lookahead=.1, settle=0) for key in "AB"}
                self._sent_strengths = {"A": 0, "B": 0}
            if not self.connected or not self._auto_enabled or self._paused or self._global_emergency_stop.is_set():
                continue
            generation = self._generation
            for channel in ("A", "B"):
                if generation != self._generation or not self._auto_enabled:
                    break
                strength = self._channel_strength(channel)
                frames = self._desired_frames[channel]
                c = 1 if channel == "B" else 0
                if self._channel_zero_pending(self.selected_client_id, self.selected_slot_id, c):
                    continue
                try:
                    if strength <= 0 or not frames:
                        players[channel].plan(now, "idle", (), enabled=False)
                        self._sent_strengths[channel] = 0
                        self._playback(channel, "", "stopped")
                        if active[channel]:
                            # End-of-event A must not block B's 100 ms stream
                            # while APP processes the acknowledged clear.
                            self._start_channel_zero(self.selected_client_id, self.selected_slot_id, c)
                            active[channel] = False
                            last_wave[channel] = ""
                        continue
                    wave_key = self._desired_wave_key[channel]
                    if now - last_send[channel] < FRAME_MS / 1000:
                        continue
                    plan = players[channel].plan(now, wave_key, frames,
                        loop=self._desired_loop[channel], transition=self._desired_transition[channel])
                    if plan.clear:
                        # V4 sends only one 100 ms frame with im=True, replacing
                        # this channel's task. The selection baseline already
                        # acknowledged zero; no second baseline is needed.
                        plan = players[channel].plan(now, wave_key, frames,
                            loop=self._desired_loop[channel], transition=self._desired_transition[channel])
                    if plan.finished:
                        if active[channel]:
                            self._start_channel_zero(self.selected_client_id, self.selected_slot_id, c)
                            active[channel] = False
                        self._sent_strengths[channel] = 0
                        self._playback(channel, wave_key, "completed")
                        continue
                    if not plan.frames:
                        continue
                    await self._rpc("device.op", {"s": self.selected_slot_id, "t": 4, "c": c, "p": 1,
                                                   "d": LEASE_MS, "v": strength, "im": True})
                    if generation != self._generation or not self._auto_enabled:
                        break
                    await self._rpc("device.op", {"s": self.selected_slot_id, "t": 0, "c": c, "p": 1,
                                                   "d": FRAME_MS, "v": list(plan.frames), "im": True})
                    self._sent_strengths[channel] = strength
                    self._playback(channel, players[channel].identity[0], "playing")
                    last_send[channel], active[channel] = now, True
                except (websockets.ConnectionClosed, ConnectionError, ValueError, TimeoutError):
                    self._request_emergency_in_loop()
                    self._emit("error", detail="V4 输出链路异常，已撤销授权")
                    break
