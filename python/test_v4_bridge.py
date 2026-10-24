"""V4 wire and safety tests; fake APP only, never Bluetooth/device output."""
import asyncio
from contextlib import suppress
from copy import deepcopy
import json
import queue
import time
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import websockets

from manaka_devices.dglab_v4 import (
    DGLabV4Bridge, LEASE_MS, MAX_PENDING, channel_block_reason, validate_v4_frames, protocol_strength,
)


def device(kind="OVC_1", slot="ovc", **props):
    return {"slotId": slot, "name": "Fake device", "type": kind,
            "props": {"connectState": "connected", "channelAStatus": True,
                      "channelBStatus": False, **props},
            "slotState": {"hasDevice": True, "channelA": {"isMuted": False},
                          "channelB": {"isMuted": False}}}


class V4UnitTests(unittest.TestCase):
    def test_discovery_log_explains_unselected_conflict_without_payload_dump(self):
        with patch("manaka_devices.dglab_bridge.ipv4_interfaces", return_value=[{"address":"127.0.0.1"}]):
            bridge = DGLabV4Bridge(queue.Queue(), port=0)
        raw = device("COYOTE_030")
        raw["slotState"]["hasDevice"] = False
        raw["name"] = "Private device name"
        bridge._devices = {"app": {raw["slotId"]:raw}}
        with patch("manaka_devices.dglab_v4.audit.record") as record:
            bridge._publish_devices()
            bridge._publish_devices()
            self.assertEqual(record.call_count, 1)
            self.assertEqual(record.call_args.args, ("socket.v4_discovery",))
            fields = record.call_args.kwargs
            self.assertEqual(fields["count"], 1)
            row = fields["devices"][0]
            self.assertIs(row["has_device"], False)
            self.assertEqual(row["connect_state"], "connected")
            self.assertEqual(row["channel_a_reason"], "bluetooth-not-connected")
            self.assertNotIn("Private device name", json.dumps(fields))
            raw["slotState"]["hasDevice"] = True
            bridge._publish_devices()
            self.assertEqual(record.call_count, 2)
        self.assertFalse(bridge.connected or bridge._auto_enabled)

    def test_ovc_intensity_floors_after_limits_and_never_changes_coyote_steps(self):
        for value, cap, expected in ((38,100,30),(41,100,40),(37,100,30),(36,100,30),
                                     (39.99,100,30),(9.99,100,0),(10,100,10),(25,25,20),
                                     (100,19,10),(100,9,0),(100,0,0),(-1,100,0),(200,100,100),
                                     (200,200,200),(199,200,190),(250,200,200),(200,155,150)):
            with self.subTest(value=value,cap=cap):
                result = protocol_strength(value,cap,"OVC_1")
                self.assertEqual(result,expected)
                self.assertLessEqual(result,max(0,min(value,cap,200)))
        for value in (float("nan"),float("inf"),None,"invalid"):
            self.assertEqual(protocol_strength(value,100,"OVC_1"),0)
        self.assertEqual(protocol_strength(37,100,"COYOTE_030"),37)
        self.assertEqual(protocol_strength(37,25,"COYOTE_030"),25)

    def test_invalid_channel_state_is_not_misreported_as_muted(self):
        raw=device("COYOTE_030")
        raw["slotState"]["channelA"]=None
        self.assertEqual(channel_block_reason(raw,"A"),"missing-device-state")

    def test_latest_device_limit_is_applied_before_ovc_step_conversion(self):
        with patch("manaka_devices.dglab_bridge.ipv4_interfaces",return_value=[{"address":"127.0.0.1"}]):
            bridge=DGLabV4Bridge(queue.Queue(),port=0)
        raw=device()
        bridge.selected_client_id,bridge.selected_slot_id,bridge.device_type="app","ovc","OVC_1"
        bridge._devices={"app":{"ovc":raw}}
        bridge._hard_cap=100
        bridge._desired_strength={"A":39.99,"B":90}
        raw["slotState"]["channelA"]["intensityMax"]=25
        self.assertEqual(bridge._channel_strength("A"),20)
        self.assertEqual(bridge._channel_strength("B"),0)
        raw["slotState"]["channelA"]["intensityMax"]=9
        self.assertEqual(bridge._channel_strength("A"),0)

    def test_ovc_200_output_request_keeps_device_limit(self):
        from unittest.mock import MagicMock
        with patch("manaka_devices.dglab_bridge.ipv4_interfaces",return_value=[{"address":"127.0.0.1"}]):
            bridge = DGLabV4Bridge(queue.Queue(), port=0)
        bridge._loop = MagicMock()
        bridge.device_type = "OVC_1"
        bridge.update_auto_outputs(200, ["0A0A0A0A64646464"], wave_key_a="ovc_beat",
                                   strength_b=199, frames_b=[], wave_key_b="idle", hard_cap=200)
        args = bridge._loop.call_soon_threadsafe.call_args.args
        self.assertEqual((args[1], args[4], args[-1]), (200, 190, 200))
        bridge.device_type = "COYOTE_030"
        bridge.update_auto_outputs(200, [], wave_key_a="idle", strength_b=200,
                                   frames_b=[], wave_key_b="idle", hard_cap=200)
        self.assertEqual(bridge._loop.call_soon_threadsafe.call_args.args[-1], 100)
        bridge._loop = None

    def test_accessory_and_fault_semantics_are_device_specific(self):
        raw = device()
        self.assertEqual(channel_block_reason(raw, "A"), "")
        self.assertEqual(channel_block_reason(raw, "B"), "accessory-not-inserted")
        raw = device("COYOTE_030", channelAStatus=0)
        self.assertEqual(channel_block_reason(raw, "A"), "")
        raw["props"]["channelAStatus"] = 3
        self.assertEqual(channel_block_reason(raw, "A"), "channel-fault-or-blocked")

    def test_optional_state_fields_and_disconnected_override(self):
        raw = {"type": "COYOTE_030", "props": {}, "slotState": {"hasDevice": True}}
        self.assertEqual(channel_block_reason(raw, "A"), "")
        raw["props"]["connectState"] = "disconnected"
        self.assertEqual(channel_block_reason(raw, "A"), "bluetooth-not-connected")
        raw["props"]["connectState"] = "connected"
        raw["slotState"]["hasDevice"] = False
        self.assertEqual(channel_block_reason(raw, "A"), "bluetooth-not-connected")

    def test_unverified_v2_waveform_route_is_disabled(self):
        self.assertEqual(channel_block_reason(device("COYOTE_020"), "A"), "unsupported-waveformat")

    def test_frames_require_complete_hex_byte_pairs(self):
        self.assertEqual(validate_v4_frames(["0a0b", "00000000"]), ("0A0B", "00000000"))
        for bad in (["ABC"], ["GG"], [""], ["00"] * 101):
            with self.assertRaises(ValueError):
                validate_v4_frames(bad)


class V4WireTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        with patch("manaka_devices.dglab_bridge.ipv4_interfaces", return_value=[{"address": "127.0.0.1"}]):
            self.bridge = DGLabV4Bridge(queue.Queue(), port=0)
        self.server = asyncio.create_task(self.bridge._run())
        await self.until(lambda: self.bridge.server_ready)
        self.phone = await websockets.connect(f"ws://127.0.0.1:{self.bridge.port}/?tid={self.bridge.controller_id}")
        hello, attached = json.loads(await self.phone.recv()), json.loads(await self.phone.recv())
        self.assertEqual(hello["type"], "hello")
        self.assertEqual(attached["type"], "controller_attached")
        self.client_id = hello["clientId"]
        self.records = []
        self.record_times = []
        self.devices = [device()]
        self.ack = True
        self.tick_ack = False
        self.tick_requests = []
        self.reader = asyncio.create_task(self.read_phone())
        await self.until(lambda: len(self.bridge.devices_snapshot()) == 1)

    async def asyncTearDown(self):
        self.bridge._stop_event.set()
        await asyncio.wait_for(self.server, 3)
        self.reader.cancel()
        with suppress(asyncio.CancelledError, websockets.ConnectionClosed):
            await self.reader
        await self.phone.close()

    async def until(self, predicate, timeout=2):
        deadline = time.monotonic() + timeout
        while not predicate():
            if time.monotonic() > deadline:
                self.fail("condition timed out")
            await asyncio.sleep(.005)

    async def read_phone(self):
        async for raw in self.phone:
            packet = json.loads(raw)
            if packet.get("type") != "message":
                continue
            data = packet["data"]
            self.records.append(data)
            self.record_times.append((time.monotonic(), data))
            if not self.ack:
                continue
            if self.tick_ack:
                self.tick_requests.append(data)
                continue
            result = {"devices": self.devices} if data["m"] == "devices.get" else (
                {"type": data["data"]["t"], "reason": "completed"} if data["m"] == "device.op" else {})
            await self.send({"t": "resp", "reqId": data["reqId"], "result": result})

    async def send(self, data):
        await self.phone.send(json.dumps({"type": "message", "data": data}))

    async def tick_responder(self, interval=.025):
        """APP-like scheduler: later im requests replace same-type queued work."""
        while True:
            await asyncio.sleep(interval)
            requests, self.tick_requests = self.tick_requests, []
            replaced = set()
            latest = {}
            for index, request in enumerate(requests):
                data = request.get("data", {})
                if request["m"] == "device.op" and data.get("im"):
                    key = (data["s"], data["c"], data["t"])
                    if key in latest:
                        replaced.add(latest[key])
                    latest[key] = index
            for index, request in enumerate(requests):
                data = request.get("data", {})
                result = ({"type": data["t"], "reason": "replaced" if index in replaced else "completed",
                           "slotId": data["s"], "channel": data["c"]}
                          if request["m"] == "device.op" else {})
                await self.send({"t": "resp", "reqId": request["reqId"], "result": result})

    async def select(self):
        self.assertTrue(self.bridge.select_device(self.client_id, "ovc"))
        await self.until(lambda: self.bridge.connected)

    def update(self, a=20, b=30, key="one", cap=25):
        self.bridge.update_auto_outputs(a, ["0000000010203040"], wave_key_a=key,
                                       strength_b=b, frames_b=["0000000040404040"], wave_key_b=key,
                                       hard_cap=cap)

    async def arm(self):
        self.update()
        await asyncio.sleep(.01)
        self.bridge.set_auto_enabled(True)
        await self.until(lambda: self.bridge._auto_enabled)

    def nonzero(self):
        return [r for r in self.records if r["m"] == "device.op" and r.get("data", {}).get("t") == 4]

    async def test_qr_and_explicit_selection_zero_barrier(self):
        params = parse_qs(urlsplit(self.bridge.qr_url).query)
        self.assertEqual(params["action"], ["socket"])
        self.assertIn("?tid=" + self.bridge.controller_id, params["url"][0])
        self.assertFalse(self.bridge.connected)
        self.update()
        self.bridge.set_auto_enabled(True)
        await asyncio.sleep(.05)
        self.assertEqual(self.nonzero(), [])
        await self.select()
        self.assertFalse(self.bridge._auto_enabled)
        operations = [(r["m"], r.get("data", {}).get("t"), r.get("data", {}).get("v"))
                      for r in self.records if r["m"] != "devices.get"]
        self.assertEqual(operations[:5], [("device.op", 7, 0), ("device.op", 7, 0),
                                         ("device.op.clear", None, None), ("device.op", 7, 0), ("device.op", 7, 0)])

    async def test_finite_leases_and_only_inserted_channel(self):
        await self.select()
        await self.arm()
        await self.until(lambda: len(self.nonzero()) >= 2)
        for request in self.nonzero():
            self.assertEqual(request["data"]["d"], LEASE_MS)
            self.assertEqual(request["data"]["c"], 0)
            self.assertEqual(request["data"]["v"], 20)
            self.assertTrue(request["data"]["im"])
        pulses = [r["data"] for r in self.records if r["m"] == "device.op" and r["data"]["t"] == 0]
        self.assertTrue(pulses)
        self.assertTrue(all(len(p["v"]) == 1 and p["d"] == 100 and p["im"] for p in pulses))

    async def test_patch_deep_merge_preserves_sibling_fields(self):
        await self.send({"t": "ev", "ev": "slots.patch", "slots": [
            {"slotId": "ovc", "slotState": {"channelA": {"isMuted": True}}}]})
        await self.until(lambda: self.bridge.devices_snapshot()[0]["slotState"]["channelA"]["isMuted"])
        snapshot = self.bridge.devices_snapshot()[0]
        self.assertTrue(snapshot["slotState"]["hasDevice"])
        self.assertEqual(snapshot["props"]["connectState"], "connected")
        self.assertFalse(snapshot["slotState"]["channelB"]["isMuted"])

    async def test_disconnect_reconnect_never_restores_selection_or_cached_output(self):
        await self.select()
        await self.arm()
        await self.until(lambda: len(self.nonzero()) > 0)
        await self.send({"t": "ev", "ev": "slots.patch", "slots": [
            {"slotId": "ovc", "slotState": {"hasDevice": False}}]})
        await self.until(lambda: not self.bridge.selected_slot_id)
        self.assertFalse(self.bridge.connected)
        self.assertEqual(self.bridge._desired_updated_at, 0)
        count = len(self.nonzero())
        await self.send({"t": "ev", "ev": "devices.snapshot", "devices": self.devices})
        self.update()
        self.bridge.set_auto_enabled(True)
        await asyncio.sleep(.15)
        self.assertEqual(len(self.nonzero()), count)

    async def test_coyote_bluetooth_waiting_retains_slot_in_standalone_adapter(self):
        self.devices = [device("COYOTE_030", "coyote", channelAStatus=0, channelBStatus=0)]
        self.devices[0]["slotState"]["hasDevice"] = False
        await self.send({"t": "ev", "ev": "devices.snapshot", "devices": self.devices})
        await self.until(lambda: self.bridge.devices_snapshot()[0]["type"] == "COYOTE_030")
        self.assertTrue(self.bridge.select_device(self.client_id, "coyote"))
        await self.until(lambda: any(payload.get("event") == "waiting" for _, payload in self.bridge.events.queue))
        self.assertEqual(self.bridge.selected_slot_id, "coyote")
        self.assertFalse(self.bridge.connected or self.bridge._auto_enabled)
        self.assertEqual(self.nonzero(), [])
        await self.send({"t": "ev", "ev": "slots.patch", "slots": [
            {"slotId": "coyote", "slotState": {"hasDevice": True}}]})
        await self.until(lambda: self.bridge.connected)
        self.assertFalse(self.bridge._auto_enabled)
        self.assertEqual(self.bridge._desired_updated_at, 0)

    async def test_pause_and_emergency_block_nonzero(self):
        await self.select()
        await self.arm()
        await self.until(lambda: len(self.nonzero()) > 0)
        self.bridge.set_paused(True)
        await self.until(lambda: self.bridge._paused)
        count = len(self.nonzero())
        self.update()
        self.bridge.set_auto_enabled(True)
        await asyncio.sleep(.15)
        self.assertEqual(len(self.nonzero()), count)
        self.bridge.set_paused(False)
        await self.until(lambda: not self.bridge._paused)
        self.bridge.latch_global_emergency_stop()
        self.update()
        self.bridge.set_auto_enabled(True)
        await asyncio.sleep(.05)
        self.assertEqual(len(self.nonzero()), count)

    async def test_watchdog_and_missing_task_responses_fail_closed(self):
        await self.select()
        await self.arm()
        await self.until(lambda: len(self.nonzero()) > 0)
        self.bridge._desired_updated_at = time.monotonic() - .6
        await self.until(lambda: not self.bridge._auto_enabled)
        event = next(p for _,p in self.bridge.events.queue if p.get("event")=="output_timeout")
        self.assertEqual(event["reason"],"producer-stale")
        self.assertGreaterEqual(event["producer_age_ms"],500)

    async def test_stalled_app_does_not_serialize_the_output_loop(self):
        await self.select()
        self.ack = False
        await self.arm()
        await self.until(lambda: len(self.nonzero()) >= 2)
        self.assertLess(len(self.bridge._pending), MAX_PENDING)
        # Lack of an immediate task-end response must not block the next frame.
        self.assertGreaterEqual(len(self.nonzero()), 2)

    async def test_missing_task_completion_with_fresh_updates_disarms(self):
        await self.select()
        self.ack = False
        await self.arm()
        await self.until(lambda: len(self.nonzero()) > 0)
        self.update()
        for pending in self.bridge._pending.values():
            if pending["method"] == "device.op" and not pending["safety"]:
                pending["deadline"] = time.monotonic() - 1
        await self.until(lambda: not self.bridge._auto_enabled)
        self.assertTrue(any(p.get("event")=="output_timeout" and p.get("reason")=="response-timeout" for _,p in self.bridge.events.queue))

    async def test_failed_write_does_not_kill_output_scheduler(self):
        await self.select()
        # _run keeps the real scheduler task alive; emulate a bounded send
        # timeout at its RPC boundary without waiting for OS buffer pressure.
        original_rpc = self.bridge._rpc
        tripped = False
        async def timeout_once(method, data, **kwargs):
            nonlocal tripped
            if not tripped and method == "device.op" and data.get("t") == 4:
                tripped = True
                raise TimeoutError("simulated bounded write")
            return await original_rpc(method, data, **kwargs)
        self.bridge._rpc = timeout_once
        self.update()
        await asyncio.sleep(.01)
        self.bridge.set_auto_enabled(True)
        await self.until(lambda: tripped and not self.bridge._auto_enabled)
        self.bridge._rpc = original_rpc
        await asyncio.wait_for(self.bridge._pause_zero_task, 1)
        await self.arm()
        await self.until(lambda: len(self.nonzero()) > 0)

    async def test_stronger_replacement_uses_temp_not_persistent_addition(self):
        await self.select()
        await self.arm()
        await self.until(lambda: len(self.nonzero()) > 0)
        self.update(a=99, key="stronger", cap=45)
        await self.until(lambda: any(r["data"]["v"] == 40 for r in self.nonzero()))
        self.assertFalse(any(r["m"] == "device.op" and r["data"]["t"] == 3 for r in self.records))

    async def test_wrong_pairing_id_cannot_receive_or_publish_devices(self):
        async with websockets.connect(f"ws://127.0.0.1:{self.bridge.port}/?tid=wrong") as other:
            packet = json.loads(await other.recv())
            self.assertEqual(packet["type"], "error")
            with self.assertRaises(websockets.ConnectionClosed):
                await other.recv()
        self.assertEqual(len(self.bridge.devices_snapshot()), 1)

    async def test_unknown_or_missing_slot_not_selected(self):
        self.assertFalse(self.bridge.select_device(self.client_id, "unknown"))
        self.assertFalse(self.bridge.connected)

    async def test_deselect_zeros_previous_slot_and_discards_authorization(self):
        await self.select()
        await self.arm()
        await self.until(lambda: bool(self.nonzero()))
        self.assertTrue(self.bridge.select_device("", ""))
        await self.until(lambda: not self.bridge.selected_slot_id)
        await asyncio.sleep(.03)
        self.assertFalse(self.bridge.connected)
        self.assertFalse(self.bridge._auto_enabled)
        self.assertEqual(self.bridge._desired_updated_at, 0)

    async def test_cancelled_baseline_does_not_authorize_output(self):
        self.ack = False
        self.assertTrue(self.bridge.select_device(self.client_id, "ovc"))
        await self.until(lambda: any(r["m"] == "device.op" for r in self.records))
        request = next(r for r in self.records if r["m"] == "device.op")
        await self.send({"t": "resp", "reqId": request["reqId"],
                         "result": {"type": 7, "reason": "cancelled"}})
        await asyncio.sleep(.03)
        self.assertFalse(self.bridge.connected)
        self.assertFalse(self.bridge._baseline_ready)

    async def test_overlapping_emergency_and_selection_share_acknowledged_zero_barrier(self):
        self.tick_ack = True
        ticks = asyncio.create_task(self.tick_responder())
        try:
            # Backend queues pause + emergency twice while switching profiles,
            # then explicitly selects the newly discovered device.
            self.bridge._set_paused_in_loop(True)
            self.bridge._request_emergency_in_loop()
            self.bridge._request_emergency_in_loop()
            self.bridge._select_in_loop(self.client_id, "ovc")
            await self.until(lambda: self.bridge.connected)
            self.assertFalse(self.bridge._route_zero_pending())
            self.assertFalse(self.bridge._auto_enabled)
            self.assertFalse(any(p.get("event") == "error" for _, p in self.bridge.events.queue))
            self.bridge.set_paused(False)
            await self.until(lambda: not self.bridge._paused)
            await self.arm()
            await self.until(lambda: bool(self.nonzero()))
        finally:
            ticks.cancel()
            with suppress(asyncio.CancelledError):
                await ticks
            self.tick_ack = False

    async def test_rapid_reselection_does_not_cancel_an_inflight_clear_transaction(self):
        self.tick_ack = True
        ticks = asyncio.create_task(self.tick_responder())
        try:
            self.bridge._select_in_loop(self.client_id, "ovc")
            await self.until(lambda: bool(self.tick_requests))
            self.bridge._select_in_loop(self.client_id, "ovc")
            self.bridge._select_in_loop(self.client_id, "ovc")
            await self.until(lambda: self.bridge.connected)
            self.assertFalse(self.bridge._route_zero_pending())
            self.assertFalse(any(p.get("event") == "error" for _, p in self.bridge.events.queue))
            self.assertEqual(len(self.bridge._zero_transactions), 0)
        finally:
            ticks.cancel()
            with suppress(asyncio.CancelledError):
                await ticks
            self.tick_ack = False

    async def test_cancelled_nonzero_task_removes_selection(self):
        await self.select()
        self.ack = False
        await self.arm()
        await self.until(lambda: bool(self.nonzero()))
        request = self.nonzero()[0]
        await self.send({"t": "resp", "reqId": request["reqId"],
                         "result": {"type": 4, "reason": "cancelled"}})
        await self.until(lambda: not self.bridge.selected_slot_id)
        self.assertFalse(self.bridge.connected)
        self.assertFalse(self.bridge._auto_enabled)

    async def test_channel_a_clear_does_not_interrupt_channel_b_stream(self):
        await self.send({"t": "ev", "ev": "slots.patch", "slots": [
            {"slotId": "ovc", "props": {"channelBStatus": True}}]})
        await self.until(lambda: not self.bridge.devices_snapshot()[0]["channelBReason"])
        await self.select()
        self.tick_ack = True
        ticks = asyncio.create_task(self.tick_responder(.1))
        try:
            await self.arm()
            await self.until(lambda: len([r for r in self.nonzero() if r["data"]["c"] == 1]) >= 2)
            started = time.monotonic()
            # A ends, is cleared over three 100ms APP ticks, then a stronger
            # event arrives before clear completion. B must keep streaming.
            a_retriggered = False
            while time.monotonic() - started < .7:
                age = time.monotonic() - started
                self.update(a=35 if age > .08 else 0, b=20, key="retrigger" if age > .08 else "off", cap=35)
                a_retriggered = a_retriggered or self.bridge._channel_zero_pending(self.client_id, "ovc", 0)
                await asyncio.sleep(.025)
            self.assertTrue(a_retriggered, "The test must exercise a real channel clear barrier")
            b_times = [stamp for stamp, r in self.record_times if stamp >= started
                       and r["m"] == "device.op" and r["data"]["t"] == 0 and r["data"]["c"] == 1]
            self.assertGreaterEqual(len(b_times), 5)
            self.assertLess(max(b - a for a, b in zip(b_times, b_times[1:])), .28)
            self.assertTrue(any(stamp > started and r["m"] == "device.op" and r["data"]["t"] == 4
                                and r["data"]["c"] == 0 and r["data"]["v"] == 30
                                for stamp, r in self.record_times))
            self.assertTrue(self.bridge._auto_enabled)
        finally:
            ticks.cancel()
            with suppress(asyncio.CancelledError):
                await ticks
            self.tick_ack = False

    async def test_immutable_snapshot_and_request_ids_unique(self):
        copy = self.bridge.devices_snapshot()
        copy[0]["name"] = "modified"
        self.assertEqual(self.bridge.devices_snapshot()[0]["name"], "Fake device")
        await self.select()
        ids = [r["reqId"] for r in self.records]
        self.assertEqual(len(ids), len(set(ids)))
