"""Loopback-only DG-LAB 4 APP fixture. No BLE or physical-device access.

This deliberately omits the Coyote 3.0 circuit-status properties from a 2.0
fixture. Responses represent task completion, not receipt of a WebSocket write.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import json
import math
import time
from urllib.parse import urlsplit

import websockets


def mock_device(kind: str = "COYOTE_020", slot: str = "coyote") -> dict:
    props = {"connectState": "connected", "intensityA": 0, "intensityB": 0}
    if kind == "COYOTE_030":
        props.update(channelAStatus=0, channelBStatus=0)
    elif kind == "OVC_1":
        props.update(channelAStatus=True, channelBStatus=True)
    cap = 200 if kind == "OVC_1" else 100
    return {
        "slotId": slot, "type": kind, "name": "Loopback " + kind,
        "props": props,
        "slotState": {"hasDevice": True,
                      "channelA": {"isMuted": False, "intensityMax": cap},
                      "channelB": {"isMuted": False, "intensityMax": cap}},
    }


def _merge(target: dict, patch: dict) -> None:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge(target[key], value)
        else:
            target[key] = deepcopy(value)


class MockV4App:
    """A strict local APP peer with independently holdable completion replies."""

    def __init__(self, *, coyote_type="COYOTE_020"):
        self.devices = [mock_device(coyote_type), mock_device("OVC_1", "ovc")]
        self.records: list[dict] = []
        self.responses: list[dict] = []
        self.errors: list[str] = []
        self.held: list[dict] = []
        self.hold_zero = False
        self.hold_clear = False
        self.hold_output = False
        self.socket = self.reader = None
        self.client_id = ""

    async def connect(self, url: str):
        if urlsplit(url).hostname not in {"127.0.0.1", "::1", "localhost"}:
            raise ValueError("Mock APP only accepts loopback URLs")
        self.socket = await websockets.connect(url)
        hello = json.loads(await self.socket.recv())
        attached = json.loads(await self.socket.recv())
        if hello.get("type") != "hello" or attached.get("type") != "controller_attached":
            raise ValueError("Unexpected V4 handshake")
        self.client_id = hello["clientId"]
        self.reader = asyncio.create_task(self._read())
        return self

    async def send(self, data: dict) -> None:
        await self.socket.send(json.dumps({"type": "message", "data": data}))

    async def patch_slot(self, slot: str, **fields) -> None:
        item = next(d for d in self.devices if d["slotId"] == slot)
        _merge(item, fields)
        await self.send({"t": "ev", "ev": "slots.patch", "slots": [{"slotId": slot, **fields}]})

    async def snapshot(self) -> None:
        """Send a replacement when testing genuinely absent fields (not null)."""
        await self.send({"t": "ev", "ev": "devices.snapshot", "devices": deepcopy(self.devices)})

    def _validate(self, request: dict) -> str:
        method, data = request.get("m"), request.get("data") or {}
        if method not in {"device.op", "device.op.clear"}:
            return ""
        device = next((d for d in self.devices if d["slotId"] == data.get("s")), None)
        if device is None:
            return "slot_not_found"
        if method == "device.op.clear":
            return ""
        if data.get("c") not in (0, 1) or data.get("p") != 1 or data.get("im") is not True:
            return "invalid_channel_or_task_flags"
        if data.get("t") == 7:
            return "" if data.get("v") == 0 else "invalid_zero"
        if data.get("t") == 0:
            frames = data.get("v")
            if data.get("d") != 100 or not isinstance(frames, list) or len(frames) != 1:
                return "waveform_must_be_one_100ms_frame"
            if any(not isinstance(frame, str) or len(frame) != 16 or
                   any(c not in "0123456789abcdefABCDEF" for c in frame) for frame in frames):
                return "waveform_must_be_eight_byte_v3_encoding"
            if device["type"] in {"COYOTE_020", "COYOTE_030"} and data.get("ver") != 3:
                return "coyote_input_encoding_requires_explicit_ver3"
        elif data.get("t") == 4:
            value = data.get("v")
            if data.get("d") != 300 or type(value) not in (int, float) or not math.isfinite(value):
                return "invalid_short_intensity_lease"
            protocol_cap = 200 if device["type"] == "OVC_1" else 100
            if not 0 <= value <= protocol_cap:
                return "intensity_outside_protocol_range"
            if device["type"] == "OVC_1" and value % 10:
                return "ovc_intensity_requires_ten_unit_steps"
        else:
            return "unexpected_task_type"
        return ""

    async def _reply(self, request: dict, *, reason: str = "completed") -> None:
        method, data = request.get("m"), request.get("data") or {}
        error = self._validate(request)
        if error:
            self.errors.append(error)
            response = {"t": "resp", "reqId": request["reqId"], "error": error}
        else:
            if method == "devices.get":
                result = {"devices": deepcopy(self.devices)}
            elif method == "device.op":
                result = {"type": data["t"], "slotId": data["s"], "channel": data["c"], "reason": reason}
                if data["t"] in {4, 7}:
                    item = next(d for d in self.devices if d["slotId"] == data["s"])
                    item["props"]["intensity" + ("B" if data["c"] else "A")] = data["v"]
            else:
                result = {}
            response = {"t": "resp", "reqId": request["reqId"], "result": result}
        await self.send(response)
        self.responses.append({"at": time.monotonic(), **deepcopy(response)})

    async def _read(self) -> None:
        try:
            async for raw in self.socket:
                outer = json.loads(raw)
                if outer.get("type") != "message":
                    continue
                request = outer["data"]
                self.records.append({"at": time.monotonic(), **deepcopy(request)})
                data = request.get("data") or {}
                if (data.get("s") == "coyote" and
                    ((self.hold_zero and request.get("m") == "device.op" and data.get("t") == 7)
                     or (self.hold_clear and request.get("m") == "device.op.clear")
                     or (self.hold_output and request.get("m") == "device.op" and data.get("t") in {0, 4}))):
                    self.held.append(request)
                    continue
                await self._reply(request)
        except websockets.ConnectionClosed:
            pass

    async def release_held(self, *, reason="completed") -> None:
        requests, self.held = self.held, []
        for request in requests:
            await self._reply(request, reason=reason)

    def tasks(self, slot="coyote", *, task_type=None, channel=None, since=0) -> list[dict]:
        return [r for r in self.records if r["at"] >= since and r.get("m") == "device.op"
                and r["data"].get("s") == slot
                and (task_type is None or r["data"].get("t") == task_type)
                and (channel is None or r["data"].get("c") == (1 if channel == "B" else 0))]

    def pulses(self, slot="coyote", channel=None, *, since=0):
        return self.tasks(slot, task_type=0, channel=channel, since=since)

    def strengths(self, slot="coyote", channel=None, *, since=0):
        return self.tasks(slot, task_type=4, channel=channel, since=since)

    async def close(self) -> None:
        if self.socket is not None:
            await self.socket.close()
        if self.reader is not None:
            await self.reader
        self.socket = self.reader = None
