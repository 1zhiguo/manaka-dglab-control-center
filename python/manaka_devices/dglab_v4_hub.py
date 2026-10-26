"""One DG-LAB 4 connection with independent electrical and vibration routes.

The two route adapters share discovery/transport only. Selection, A/B output,
strength caps, queue cursors, watchdogs and pending RPCs are separate. A missing
or faulty OVC therefore cannot replace or stop a healthy Coyote route.
"""
from __future__ import annotations

import asyncio
import queue
import time
import uuid

from . import audit
from .dglab_v4 import DGLabV4Bridge, V4_PORT


ROLE_TYPES = {"coyote": frozenset({"COYOTE_030"}), "ovc": frozenset({"OVC_1"})}


class _RoleBridge(DGLabV4Bridge):
    def __init__(self, hub: "DGLabV4Hub", role: str):
        super().__init__(hub.events, port=hub.requested_port, lan_ip=hub.lan_ip)
        self._hub = hub
        self.role = role
        self._request_id_prefix = role + ":"

    def _emit(self, event: str, **payload) -> None:
        if event in {"connected", "waiting", "disconnected", "error", "output_timeout"}:
            audit.record("socket.v4_route_state", role=self.role, state=event,
                         connected=self.connected, app_client_id=self.selected_client_id,
                         slot_id=self.selected_slot_id, reason=payload.get("reason"),
                         detail=str(payload.get("detail", ""))[:300],
                         producer_age_ms=payload.get("producer_age_ms"), pending_count=len(self._pending))
        super()._emit(event, **{**payload, "role": self.role, "protocol": "v4",
                               "selection_epoch": self._selection_epoch})

    def select_device(self, client_id: str, slot_id: str) -> bool:
        if client_id or slot_id:
            item = next((item for item in self.devices_snapshot()
                         if item["clientId"] == client_id and item["slotId"] == slot_id), None)
            if item is None or item.get("type") not in ROLE_TYPES[self.role]:
                return False
            if any(other is not self and other.selected_client_id == client_id
                   and other.selected_slot_id == slot_id for other in self._hub._channels.values()):
                return False
        return super().select_device(client_id, slot_id)

    def start(self) -> None:
        self._hub.start()

    def stop(self, timeout: float = 2.0) -> None:
        # Releasing the electrical route must not close OVC's shared APP.
        self.emergency_stop()
        self.select_device("", "")

    def set_lan_ip(self, address: str) -> bool:
        return self._hub.set_lan_ip(address)

    def refresh_lan_ips(self) -> None:
        self._hub.refresh_lan_ips()

    def _close_for_route_error(self, client_id: str, reason: str) -> None:
        # A route-level RPC rejection/timeout is not proof that the shared APP
        # is dead. Discard this role's authority without cutting off its peer.
        self._discard_outputs()
        self.connected = self._baseline_ready = False
        self._selection_waiting_for_ready = False
        self._readiness_failure_latched = True
        self._waiting_signature = None
        audit.record("socket.v4_route_failure", role=self.role,
                     app_client_id=client_id, slot_id=self.selected_slot_id, reason=reason)
        self._emit("disconnected", reason=reason)

    def _attach(self, hub: "DGLabV4Hub") -> None:
        self._loop = hub._loop
        self._clients = hub._clients
        self._devices = hub._devices
        self.port, self.lan_ip = hub.port, hub.lan_ip
        self.controller_id, self.qr_url = hub.controller_id, hub.qr_url
        self.server_ready = hub.server_ready
        self.app_connected = hub.app_connected
        self.available_lan_interfaces = hub.available_lan_interfaces
        self.available_lan_ips = hub.available_lan_ips

    def _reset_session(self) -> None:
        self._discard_outputs()
        self._pending.clear()
        self._zero_locks.clear()
        self._zero_transactions.clear()
        self._channel_zero_transactions.clear()
        self._pause_zero_task = None
        self._pause_epoch += 1
        self._paused = self._pause_requested
        self._selection_epoch += 1
        self._selection_task = None
        self._selection_waiting_for_ready = False
        self._readiness_failure_latched = False
        self._waiting_signature = None
        self.connected = self._baseline_ready = False
        self.selected_client_id = self.selected_slot_id = self.device_type = self.target_id = ""


class DGLabV4Hub(DGLabV4Bridge):
    """Own one local V4 server and two explicit, independent output senders."""

    def __init__(self, events: queue.Queue, *, port: int = V4_PORT, lan_ip: str = ""):
        super().__init__(events, port=port, lan_ip=lan_ip)
        self.role = "hub"
        self._request_id_prefix = "hub:"
        self._channels = {role: _RoleBridge(self, role) for role in ROLE_TYPES}

    def channel(self, role: str) -> DGLabV4Bridge:
        if role not in self._channels:
            raise ValueError("Unknown V4 output role")
        return self._channels[role]

    def select_device(self, role: str, client_id: str, slot_id: str) -> bool:
        return self.channel(role).select_device(client_id, slot_id)

    def _emit(self, event: str, **payload) -> None:
        super()._emit(event, **{**payload, "role": "hub", "protocol": "v4"})

    def emergency_stop(self) -> None:
        for channel in self._channels.values():
            channel.emergency_stop()

    def latch_global_emergency_stop(self) -> None:
        for channel in self._channels.values():
            channel.latch_global_emergency_stop()

    def clear_global_emergency_stop(self) -> None:
        for channel in self._channels.values():
            channel.clear_global_emergency_stop()

    def set_paused(self, paused: bool) -> None:
        for channel in self._channels.values():
            channel.set_paused(paused)

    def set_lan_ip(self, address: str) -> bool:
        accepted = super().set_lan_ip(address)
        if accepted:
            for channel in self._channels.values():
                channel._attach(self)
        return accepted

    def refresh_lan_ips(self) -> None:
        super().refresh_lan_ips()
        for channel in self._channels.values():
            channel.available_lan_interfaces = self.available_lan_interfaces
            channel.available_lan_ips = self.available_lan_ips

    def _handle_app_data(self, client_id: str, data: dict) -> None:
        if data.get("t") == "resp":
            req_id = data.get("reqId")
            for channel in self._channels.values():
                if isinstance(req_id, str) and req_id in channel._pending:
                    channel._handle_app_data(client_id, data)
                    return
        super()._handle_app_data(client_id, data)

    def _publish_devices(self) -> None:
        super()._publish_devices()
        for channel in self._channels.values():
            channel._attach(self)
            # APP disconnect invalidates both routes; removal of one device
            # invalidates only its owner. The other role retains its stream.
            for req_id, pending in list(channel._pending.items()):
                if pending["client_id"] not in self._clients:
                    channel._finish_pending(req_id, error=ConnectionError("APP disconnected"))
            channel._check_selected()
            channel._publish_devices()

    async def _request_watchdog(self) -> None:
        # Discovery requests belong to the hub rather than an output worker.
        while True:
            await asyncio.sleep(.1)
            for req_id, pending in list(self._pending.items()):
                if pending["deadline"] < time.monotonic():
                    self._finish_pending(req_id, error=TimeoutError("V4 discovery timed out"))

    async def _run(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._stop_event = asyncio.Event()
        self._clients.clear()
        self._devices.clear()
        self._pending.clear()
        self.app_connected = False
        self.server_ready = False
        self.qr_url = ""
        self.controller_id = str(uuid.uuid4())
        for channel in self._channels.values():
            channel._reset_session()
            channel._attach(self)
        if not await self._listen():
            return
        self.server_ready = True
        self.qr_url = self._build_qr_url()
        for channel in self._channels.values():
            channel._attach(self)
        self._emit("ready", qr_url=self.qr_url, lan_ip=self.lan_ip,
                   port=self.port, controller_id=self.controller_id)
        outputs = [asyncio.create_task(channel._output_loop()) for channel in self._channels.values()]
        watchdog = asyncio.create_task(self._request_watchdog())
        try:
            await self._stop_event.wait()
        finally:
            for channel in self._channels.values():
                channel._discard_outputs()
            await asyncio.gather(*(channel._safe_zero_async() for channel in self._channels.values()),
                                 return_exceptions=True)
            selections = []
            for channel in self._channels.values():
                if channel._selection_task is not None and not channel._selection_task.done():
                    channel._selection_task.cancel()
                    selections.append(channel._selection_task)
            for task in [*outputs, watchdog]:
                task.cancel()
            await asyncio.gather(*outputs, watchdog, *selections, return_exceptions=True)
            self._server.close()
            await self._server.wait_closed()
            zeros = [task for channel in self._channels.values()
                     for task in [*channel._zero_transactions.values(), *channel._channel_zero_transactions.values()]]
            await asyncio.gather(*zeros, return_exceptions=True)
            self.server_ready = self.app_connected = False
            self.qr_url = ""
            self._publish_devices()
            for channel in self._channels.values():
                channel._mark_disconnected()
                channel.server_ready = False
