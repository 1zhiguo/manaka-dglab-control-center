"""Concurrent Coyote/OVC routing against one fake APP; never real hardware."""
import asyncio
from contextlib import suppress
from copy import deepcopy
import json
import queue
import time
import unittest
from unittest.mock import patch

import websockets

from manaka_devices.dglab_v4_hub import DGLabV4Hub
from manaka_devices.dglab_bridge import DGLabBridge
from test_v4_bridge import device


class V4HubTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        with patch("manaka_devices.dglab_bridge.ipv4_interfaces", return_value=[{"address": "127.0.0.1"}]):
            self.hub = DGLabV4Hub(queue.Queue(), port=0)
        self.coyote, self.ovc = self.hub.channel("coyote"), self.hub.channel("ovc")
        self.server = asyncio.create_task(self.hub._run())
        await self.until(lambda: self.hub.server_ready)
        self.phone = await websockets.connect(f"ws://127.0.0.1:{self.hub.port}/?tid={self.hub.controller_id}")
        hello, attached = json.loads(await self.phone.recv()), json.loads(await self.phone.recv())
        self.assertEqual(attached["type"], "controller_attached")
        self.app_id = hello["clientId"]
        self.devices = [device("COYOTE_030", "coyote", channelAStatus=0, channelBStatus=0), device()]
        self.records, self.record_times = [], []
        self.fail_ovc_zero = False
        self.fail_coyote_zero = False
        self.hold_coyote_zero = False
        self.held_coyote_requests = []
        self.hold_coyote_output = False
        self.held_coyote_outputs = []
        self.reader = asyncio.create_task(self.read_phone())
        await self.until(lambda: len(self.hub.devices_snapshot()) == 2)

    async def asyncTearDown(self):
        self.hub._stop_event.set()
        await asyncio.wait_for(self.server, 4)
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
            outer = json.loads(raw)
            if outer.get("type") != "message":
                continue
            self.assertNotIn("clientId", outer)  # Official server→APP shape.
            request = outer["data"]
            self.records.append(request)
            self.record_times.append((time.monotonic(), request))
            if request["m"] == "devices.get":
                result = {"devices": self.devices}
            elif request["m"] == "device.op":
                data = request["data"]
                if data["s"] == "ovc" and data["t"] in {4,7} and data["v"] % 10:
                    await self.send({"t":"resp","reqId":request["reqId"],"error":"value_must_be_multiple_of_10"})
                    continue
                if self.hold_coyote_zero and data["s"] == "coyote" and data["t"] == 7:
                    self.held_coyote_requests.append(request)
                    continue
                if self.hold_coyote_output and data["s"] == "coyote" and data["t"] in {0, 4}:
                    self.held_coyote_outputs.append(request)
                    continue
                rejected = ((self.fail_ovc_zero and data["s"] == "ovc")
                            or (self.fail_coyote_zero and data["s"] == "coyote" and data["t"] == 7))
                result = {"type": data["t"], "slotId": data["s"], "channel": data["c"],
                          "reason": "cancelled" if rejected else "completed"}
            else:
                result = {}
            await self.send({"t": "resp", "reqId": request["reqId"], "result": result})

    async def send(self, data):
        await self.phone.send(json.dumps({"type": "message", "data": data}))

    async def select(self, role):
        self.assertTrue(self.hub.select_device(role, self.app_id, role))
        await self.until(lambda: self.hub.channel(role).connected)

    def update(self, route, value=10):
        route.update_auto_outputs(value, ["0A0A0A0A32323232"], wave_key_a="test",
                                  strength_b=0, frames_b=(), wave_key_b="idle", hard_cap=15)

    async def arm(self, route, value=10):
        self.update(route, value)
        await asyncio.sleep(.01)
        route.set_auto_enabled(True)
        await self.until(lambda: route._auto_enabled)

    def nonzero(self, slot=None):
        return [r for r in self.records if r["m"] == "device.op" and r["data"]["t"] == 4
                and r["data"].get("v", 0) > 0 and (slot is None or r["data"]["s"] == slot)]

    def role_events(self, role, event):
        return [payload for _, payload in self.hub.events.queue
                if payload.get("role") == role and payload.get("event") == event]

    async def coyote_patch(self, **fields):
        await self.send({"t": "ev", "ev": "slots.patch", "slots": [{"slotId": "coyote", **fields}]})

    async def test_ovc_decay_values_follow_app_ten_step_requirement(self):
        await self.select("ovc")
        for requested,cap,expected in ((38,100,30),(41,100,40),(37,25,20),(36,100,30),(39.99,100,30)):
            count=len(self.nonzero("ovc"))
            self.ovc.update_auto_outputs(requested,["0A0A0A0A32323232"],wave_key_a="step-test",
                strength_b=0,frames_b=(),wave_key_b="idle",hard_cap=cap)
            await asyncio.sleep(.01)
            self.ovc.set_auto_enabled(True)
            await self.until(lambda:len(self.nonzero("ovc"))>count)
            self.assertEqual(self.nonzero("ovc")[-1]["data"]["v"],expected)
            self.assertTrue(self.ovc.connected)
        self.assertFalse(self.role_events("ovc","error"))

    async def test_substep_ovc_request_stays_zero_without_affecting_coyote(self):
        await self.select("coyote")
        await self.select("ovc")
        await self.arm(self.coyote,7)
        await self.arm(self.ovc,9.99)
        for _ in range(6):
            self.update(self.coyote,7)
            self.update(self.ovc,9.99)
            await asyncio.sleep(.07)
        self.assertFalse(self.nonzero("ovc"))
        self.assertTrue(self.nonzero("coyote"))
        self.assertTrue(all(r["data"]["v"]==7 for r in self.nonzero("coyote")))

    async def initially_waiting_coyote(self):
        await self.coyote_patch(slotState={"hasDevice": False})
        await self.until(lambda: self.coyote.devices_snapshot()[0]["channelAReason"] == "bluetooth-not-connected")
        self.assertTrue(self.hub.select_device("coyote", self.app_id, "coyote"))
        await self.until(lambda: bool(self.role_events("coyote", "waiting")))

    async def test_coyote_initial_false_keeps_selection_and_waits_for_confirmed_baseline(self):
        await self.initially_waiting_coyote()
        # This is the logged contradiction: stale-looking props must never
        # override the explicit hasDevice=False inhibit signal.
        self.assertEqual(self.coyote._selected_device()["props"]["connectState"], "connected")
        self.assertEqual((self.coyote.selected_client_id, self.coyote.selected_slot_id,
                          self.coyote.device_type, self.coyote.target_id),
                         (self.app_id, "coyote", "COYOTE_030", self.app_id))
        self.assertFalse(self.coyote.connected or self.coyote._baseline_ready)
        waiting = self.role_events("coyote", "waiting")[0]
        self.assertEqual((waiting["reason"], waiting["target_id"], waiting["slot_id"], waiting["device_type"]),
                         ("bluetooth-not-connected", self.app_id, "coyote", "COYOTE_030"))
        for _ in range(6):
            await self.coyote_patch(slotState={"hasDevice": False})
            self.update(self.coyote)
            self.coyote.set_auto_enabled(True)
        await asyncio.sleep(.06)
        self.assertEqual(len(self.role_events("coyote", "waiting")), 1)
        self.assertEqual(self.nonzero("coyote"), [])
        self.assertFalse(any(r["m"] in {"device.op", "device.op.clear"} for r in self.records))
        await self.coyote_patch(slotState={"hasDevice": True})
        await self.until(lambda: self.coyote.connected)
        operations = [r for r in self.records if r["reqId"].startswith("coyote:")]
        self.assertEqual([r["m"] for r in operations],
                         ["device.op", "device.op", "device.op.clear", "device.op", "device.op"])
        self.assertFalse(self.coyote._auto_enabled)
        self.assertEqual(self.coyote._desired_updated_at, 0)
        await asyncio.sleep(.12)
        self.assertEqual(self.nonzero("coyote"), [])
        await self.arm(self.coyote, 7)  # Explicit resume with fresh producer data.
        await self.until(lambda: bool(self.nonzero("coyote")))

    async def test_announced_coyote_auto_selection_waits_for_true_has_device(self):
        from test_manaka_ovc import Harness
        from qml_dashboard_prototype import v4_integration
        await self.coyote_patch(slotState={"hasDevice":False})
        await self.until(lambda:self.hub.devices_snapshot()[0]["slotState"]["hasDevice"] is False)
        backend = Harness()
        backend.socket_protocol = "v4"
        backend.v4_hub = self.hub
        backend.bridge = self.coyote
        backend.auto_output_enabled = False
        with patch.object(v4_integration.audit, "record"):
            backend._auto_select_new_v4_devices(self.hub.devices_snapshot())
        await self.until(lambda:self.coyote.selected_slot_id == "coyote" and self.coyote._selection_task is not None and self.coyote._selection_task.done())
        self.assertFalse(self.coyote.connected)
        self.assertFalse(self.coyote._auto_enabled)
        self.assertEqual(self.nonzero(), [])
        await self.coyote_patch(slotState={"hasDevice":True})
        await self.until(lambda:self.coyote.connected)
        self.assertFalse(self.coyote._auto_enabled)
        self.assertFalse(backend.auto_output_enabled)
        self.assertEqual(self.nonzero(), [])

    async def test_coyote_waiting_recovery_preserves_ovc_stream_and_has_no_zero_storm(self):
        await self.select("coyote")
        await self.select("ovc")
        await self.arm(self.coyote, 7)
        await self.arm(self.ovc, 11)
        async def feed_ovc():
            while True:
                self.update(self.ovc, 11)
                await asyncio.sleep(.025)
        producer = asyncio.create_task(feed_ovc())
        async def stop_producer():
            producer.cancel()
            with suppress(asyncio.CancelledError):
                await producer
        self.addAsyncCleanup(stop_producer)
        await self.until(lambda: bool(self.nonzero("coyote")) and bool(self.nonzero("ovc")))
        await self.coyote_patch(slotState={"hasDevice": False})
        await self.until(lambda: bool(self.role_events("coyote", "waiting")))
        await self.until(lambda: sum(r["m"] == "device.op.clear" and r["data"]["s"] == "coyote"
                                    for r in self.records) >= 2 and not self.coyote._zero_transactions)
        await asyncio.sleep(.025)
        coyote_count, ovc_count = len(self.nonzero("coyote")), len(self.nonzero("ovc"))
        zero_count = sum(r["m"] == "device.op.clear" and r["data"]["s"] == "coyote" for r in self.records)
        for _ in range(3):
            await self.coyote_patch(slotState={"hasDevice": False})
            self.update(self.coyote, 7)
            self.coyote.set_auto_enabled(True)
            self.update(self.ovc, 11)
            await asyncio.sleep(.1)
        self.assertEqual(len(self.nonzero("coyote")), coyote_count)
        self.assertGreater(len(self.nonzero("ovc")), ovc_count)
        self.assertEqual(sum(r["m"] == "device.op.clear" and r["data"]["s"] == "coyote" for r in self.records), zero_count)
        self.assertEqual(self.coyote.selected_slot_id, "coyote")
        self.assertTrue(self.ovc.connected)
        await self.coyote_patch(slotState={"hasDevice": True})
        await self.until(lambda: self.coyote.connected)
        self.assertEqual(len(self.role_events("coyote", "connected")), 2)
        self.assertFalse(self.coyote._auto_enabled)
        self.assertEqual(self.coyote._desired_updated_at, 0)
        self.assertTrue(self.ovc._auto_enabled)

    async def test_coyote_both_muted_waits_without_discarding_slot(self):
        await self.select("coyote")
        await self.coyote_patch(slotState={"channelA": {"isMuted": True}, "channelB": {"isMuted": True}})
        await self.until(lambda: bool(self.role_events("coyote", "waiting")))
        self.assertEqual(self.coyote.selected_slot_id, "coyote")
        self.assertFalse(self.coyote.connected)
        self.assertEqual(self.role_events("coyote", "waiting")[-1]["reason"], "channel-muted")
        await self.coyote_patch(slotState={"channelA": {"isMuted": False}})
        await self.until(lambda: self.coyote.connected)
        self.assertFalse(self.coyote._auto_enabled)

    async def test_waiting_coyote_removal_really_deselects_with_old_route_identity(self):
        await self.initially_waiting_coyote()
        await self.send({"t": "ev", "ev": "devices.patch", "removed": ["coyote"], "added": []})
        await self.until(lambda: not self.coyote.selected_slot_id)
        event = self.role_events("coyote", "disconnected")[-1]
        self.assertEqual((event["target_id"], event["slot_id"], event["device_type"]),
                         (self.app_id, "coyote", "COYOTE_030"))
        self.assertFalse(self.coyote.connected or self.coyote._selection_waiting_for_ready)

    async def test_waiting_coyote_type_change_really_deselects(self):
        await self.initially_waiting_coyote()
        replacement = device("OVC_1", "coyote")
        await self.send({"t": "ev", "ev": "devices.patch", "removed": [], "added": [replacement]})
        await self.until(lambda: not self.coyote.selected_slot_id)
        self.assertFalse(self.coyote.connected)

    async def test_coyote_recovery_zero_failure_latches_until_explicit_reselection(self):
        await self.select("ovc")
        await self.arm(self.ovc, 11)
        await self.initially_waiting_coyote()
        self.fail_coyote_zero = True
        await self.coyote_patch(slotState={"hasDevice": True})
        await self.until(lambda: bool(self.role_events("coyote", "error")))
        self.assertFalse(self.coyote.connected or self.coyote._baseline_ready or self.coyote._auto_enabled)
        self.assertTrue(self.coyote._readiness_failure_latched)
        self.assertFalse(self.coyote._selection_waiting_for_ready)
        self.assertTrue(self.hub.app_connected and self.ovc.connected)
        zero_count = len([r for r in self.records if r["reqId"].startswith("coyote:")])
        ovc_count = len(self.nonzero("ovc"))
        for present in (False, True, True):
            await self.coyote_patch(slotState={"hasDevice": present})
            self.update(self.coyote)
            self.coyote.set_auto_enabled(True)
            self.update(self.ovc, 11)
            await asyncio.sleep(.08)
        self.assertFalse(self.coyote.connected)
        self.assertEqual(len([r for r in self.records if r["reqId"].startswith("coyote:")]), zero_count)
        self.assertGreater(len(self.nonzero("ovc")), ovc_count)
        self.assertEqual(self.nonzero("coyote"), [])
        self.fail_coyote_zero = False
        await self.select("coyote")
        self.assertFalse(self.coyote._auto_enabled)
        self.assertFalse(self.coyote._readiness_failure_latched)

    async def test_invalid_tick_cancels_old_preparation_epoch_without_losing_selection(self):
        self.hold_coyote_zero = True
        self.assertTrue(self.hub.select_device("coyote", self.app_id, "coyote"))
        await self.until(lambda: len(self.held_coyote_requests) == 2)
        old_epoch = self.coyote._selection_epoch
        await self.coyote_patch(slotState={"hasDevice": False})
        await self.until(lambda: bool(self.role_events("coyote", "waiting")))
        self.assertGreater(self.coyote._selection_epoch, old_epoch)
        self.assertEqual(self.coyote.selected_slot_id, "coyote")
        await self.coyote_patch(slotState={"hasDevice": True})
        self.hold_coyote_zero = False
        for request in self.held_coyote_requests:
            data = request["data"]
            await self.send({"t": "resp", "reqId": request["reqId"], "result": {
                "type": 7, "reason": "completed", "slotId": data["s"], "channel": data["c"]}})
        await self.until(lambda: self.coyote.connected)
        self.assertEqual(len(self.role_events("coyote", "connected")), 1)
        self.assertFalse(self.coyote._auto_enabled)
        self.assertFalse(self.coyote._readiness_failure_latched)
        self.assertEqual(self.nonzero("coyote"), [])

    async def test_old_cancelled_coyote_tasks_do_not_erase_waiting_or_recovered_selection(self):
        await self.select("coyote")
        self.hold_coyote_output = True
        await self.arm(self.coyote)
        await self.until(lambda: len(self.held_coyote_outputs) >= 2)
        await self.coyote_patch(slotState={"hasDevice": False})
        await self.until(lambda: bool(self.role_events("coyote", "waiting")))
        async def cancel(request):
            data = request["data"]
            await self.send({"t": "resp", "reqId": request["reqId"], "result": {
                "type": data["t"], "reason": "cancelled", "slotId": data["s"], "channel": data["c"]}})
            await self.until(lambda: request["reqId"] not in self.coyote._pending)
        await cancel(self.held_coyote_outputs[0])
        self.assertEqual(self.coyote.selected_slot_id, "coyote")
        self.assertFalse(self.coyote.connected)
        await self.coyote_patch(slotState={"hasDevice": True})
        await self.until(lambda: self.coyote.connected)
        await cancel(self.held_coyote_outputs[1])
        self.assertEqual(self.coyote.selected_slot_id, "coyote")
        self.assertTrue(self.coyote.connected)
        self.assertFalse(self.coyote._auto_enabled)
        self.assertEqual(self.role_events("coyote", "disconnected"), [])
        self.hold_coyote_output = False

    async def test_current_coyote_cancelled_output_still_fails_closed(self):
        await self.select("coyote")
        self.hold_coyote_output = True
        await self.arm(self.coyote)
        await self.until(lambda: bool(self.held_coyote_outputs))
        request = self.held_coyote_outputs[0]
        data = request["data"]
        await self.send({"t": "resp", "reqId": request["reqId"], "result": {
            "type": data["t"], "reason": "cancelled", "slotId": data["s"], "channel": data["c"]}})
        await self.until(lambda: not self.coyote.selected_slot_id)
        self.assertFalse(self.coyote.connected or self.coyote._auto_enabled)
        self.assertEqual(self.role_events("coyote", "disconnected")[-1]["reason"],
                         "output-task-cancelled-or-invalid")
        self.hold_coyote_output = False

    async def test_one_app_can_drive_coyote_and_ovc_independently(self):
        self.assertFalse(self.coyote.connected or self.ovc.connected)
        await self.select("coyote")
        await self.select("ovc")
        await self.arm(self.coyote, 7)
        await self.arm(self.ovc, 11)
        for _ in range(4):
            self.update(self.coyote, 7)
            self.update(self.ovc, 11)
            await asyncio.sleep(.1)
        self.assertGreaterEqual(len(self.nonzero("coyote")), 3)
        self.assertGreaterEqual(len(self.nonzero("ovc")), 3)
        self.assertTrue(all(r["data"]["v"] == 7 for r in self.nonzero("coyote")))
        self.assertTrue(all(r["data"]["v"] == 10 for r in self.nonzero("ovc")))
        ids = [r["reqId"] for r in self.records]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(any(value.startswith("coyote:") for value in ids))
        self.assertTrue(any(value.startswith("ovc:") for value in ids))

    async def test_role_kind_is_explicit_no_replacement_by_wrong_device(self):
        self.assertFalse(self.hub.select_device("coyote", self.app_id, "ovc"))
        self.assertFalse(self.hub.select_device("ovc", self.app_id, "coyote"))
        self.assertEqual(self.nonzero(), [])
        self.assertEqual(self.coyote.selected_slot_id, "")
        self.assertEqual(self.ovc.selected_slot_id, "")

    async def test_concurrent_zero_barriers_never_address_peer_device(self):
        # Both baseline transactions share one websocket and complete together;
        # neither a clear nor an A/B zero may escape its role's physical slot.
        self.assertTrue(self.hub.select_device("coyote", self.app_id, "coyote"))
        self.assertTrue(self.hub.select_device("ovc", self.app_id, "ovc"))
        await self.until(lambda: self.coyote.connected and self.ovc.connected)
        for role in ("coyote", "ovc"):
            operations = [request for request in self.records
                          if request["reqId"].startswith(role + ":")]
            self.assertEqual(len(operations), 5)
            self.assertEqual([request["m"] for request in operations],
                             ["device.op", "device.op", "device.op.clear", "device.op", "device.op"])
            self.assertTrue(all(request["data"]["s"] == role for request in operations))
            zeros = [request["data"] for request in operations if request["m"] == "device.op"]
            self.assertEqual([request["c"] for request in zeros], [0, 1, 0, 1])
            self.assertTrue(all(request["t"] == 7 and request["v"] == 0 for request in zeros))
        await self.arm(self.coyote, 7)
        await self.arm(self.ovc, 11)
        await self.until(lambda: self.nonzero("coyote") and self.nonzero("ovc"))
        self.hub.latch_global_emergency_stop()
        await self.until(lambda: all(sum(request["m"] == "device.op.clear"
                                        and request["data"]["s"] == role for request in self.records) >= 2
                                    for role in ("coyote", "ovc"))
                         and not self.coyote._zero_transactions and not self.ovc._zero_transactions)
        for request in self.records:
            if request["m"] not in {"device.op", "device.op.clear"}:
                continue
            self.assertEqual(request["reqId"].split(":", 1)[0], request["data"]["s"])

    async def test_vibration_pause_keeps_electrical_stream_alive(self):
        await self.select("coyote")
        await self.select("ovc")
        await self.arm(self.coyote)
        await self.arm(self.ovc)
        await self.until(lambda: self.nonzero("ovc"))
        self.ovc.set_paused(True)
        await self.until(lambda: self.ovc._paused)
        ovc_count, coyote_count = len(self.nonzero("ovc")), len(self.nonzero("coyote"))
        for _ in range(3):
            self.update(self.coyote)
            await asyncio.sleep(.1)
        self.assertEqual(len(self.nonzero("ovc")), ovc_count)
        self.assertGreater(len(self.nonzero("coyote")), coyote_count)

    async def test_ovc_device_removal_does_not_disconnect_coyote(self):
        await self.select("coyote")
        await self.select("ovc")
        await self.arm(self.coyote)
        await self.arm(self.ovc)
        await self.send({"t": "ev", "ev": "devices.patch", "removed": ["ovc"], "added": []})
        await self.until(lambda: not self.ovc.selected_slot_id)
        self.assertTrue(self.coyote.connected)
        count = len(self.nonzero("coyote"))
        for _ in range(3):
            self.update(self.coyote)
            await asyncio.sleep(.1)
        self.assertGreater(len(self.nonzero("coyote")), count)

    async def test_failed_ovc_baseline_does_not_close_shared_app(self):
        await self.select("coyote")
        await self.arm(self.coyote)
        self.fail_ovc_zero = True
        self.assertTrue(self.hub.select_device("ovc", self.app_id, "ovc"))
        await self.until(lambda: self.ovc._selection_task is not None and self.ovc._selection_task.done())
        self.assertFalse(self.ovc.connected)
        self.assertTrue(self.coyote.connected)
        self.assertTrue(self.hub.app_connected)
        count = len(self.nonzero("coyote"))
        for _ in range(3):
            self.update(self.coyote)
            await asyncio.sleep(.1)
        self.assertGreater(len(self.nonzero("coyote")), count)

    async def test_global_emergency_stop_latches_both_roles(self):
        await self.select("coyote")
        await self.select("ovc")
        await self.arm(self.coyote)
        await self.arm(self.ovc)
        await self.until(lambda: self.nonzero("ovc"))
        generations = {route: route._generation for route in (self.coyote, self.ovc)}
        self.hub.latch_global_emergency_stop()
        self.assertTrue(self.coyote._global_emergency_stop.is_set())
        self.assertTrue(self.ovc._global_emergency_stop.is_set())
        # A command written before Stop can still be in flight to the fake App.
        # Establish the boundary using acknowledged zero/clear completion,
        # rather than a scheduler-dependent 30 ms delivery assumption.
        await self.until(lambda: all(route._generation > generations[route]
                         and route._pause_zero_task is not None and route._pause_zero_task.done()
                         for route in (self.coyote, self.ovc)))
        for route in (self.coyote, self.ovc):
            self.assertFalse(route._auto_enabled)
            self.assertEqual(route._desired_strength, {"A": 0, "B": 0})
        count = len(self.nonzero())
        self.update(self.coyote)
        self.update(self.ovc)
        self.coyote.set_auto_enabled(True)
        self.ovc.set_auto_enabled(True)
        await asyncio.sleep(.2)
        self.assertEqual(len(self.nonzero()), count)

    async def test_slot_announced_before_accessory_state_retries_readiness_not_output(self):
        raw = deepcopy(self.devices[1])
        raw["props"]["channelAStatus"] = False
        await self.send({"t": "ev", "ev": "devices.snapshot", "devices": [self.devices[0], raw]})
        await self.until(lambda: self.ovc.devices_snapshot()[1]["channelAReason"] == "accessory-not-inserted")
        self.assertTrue(self.hub.select_device("ovc", self.app_id, "ovc"))
        await self.until(lambda: self.ovc._selection_task is not None and self.ovc._selection_task.done())
        self.assertFalse(self.ovc.connected)
        await self.send({"t": "ev", "ev": "slots.patch", "slots": [
            {"slotId": "ovc", "props": {"channelAStatus": True}}]})
        await self.until(lambda: self.ovc.connected)
        self.assertFalse(self.ovc._auto_enabled)
        self.assertEqual(self.nonzero(), [])

    async def test_app_disconnect_invalidates_both_routes(self):
        await self.select("coyote")
        await self.select("ovc")
        await self.phone.close()
        await self.until(lambda: not self.coyote.connected and not self.ovc.connected)
        self.assertEqual((self.coyote.selected_slot_id, self.ovc.selected_slot_id), ("", ""))

    async def test_releasing_coyote_route_does_not_stop_vibration(self):
        await self.select("coyote")
        await self.select("ovc")
        await self.arm(self.coyote)
        await self.arm(self.ovc)
        self.coyote.stop()
        await self.until(lambda: not self.coyote.selected_slot_id)
        count = len(self.nonzero("ovc"))
        for _ in range(3):
            self.update(self.ovc)
            await asyncio.sleep(.1)
        self.assertTrue(self.ovc.connected)
        self.assertGreater(len(self.nonzero("ovc")), count)

    async def test_legacy_v3_electrical_output_coexists_with_v4_vibration(self):
        with patch("manaka_devices.dglab_bridge.ipv4_interfaces", return_value=[{"address": "127.0.0.1"}]):
            legacy = DGLabBridge(queue.Queue(), port=0)
        legacy_server = asyncio.create_task(legacy._run())
        legacy_phone = None
        reader = None
        received = []
        try:
            await self.until(lambda: legacy.server_ready and legacy.controller_id)
            legacy_phone = await websockets.connect(f"ws://127.0.0.1:{legacy.port}/")
            hello = json.loads(await legacy_phone.recv())
            await legacy_phone.send(json.dumps({"type": "bind", "clientId": legacy.controller_id,
                "targetId": hello["clientId"], "message": "DGLAB"}))
            async def read_legacy():
                async for raw in legacy_phone:
                    received.append(json.loads(raw))
            reader = asyncio.create_task(read_legacy())
            await self.until(lambda: legacy.connected)
            await self.select("ovc")
            await self.arm(legacy, 6)
            await self.arm(self.ovc, 10)
            for _ in range(3):
                self.update(legacy, 6)
                self.update(self.ovc, 10)
                await asyncio.sleep(.1)
            self.assertTrue(any(item.get("message", "").startswith("pulse-A:") for item in received))
            self.assertTrue(any(item.get("message") == "strength-1+2+6" for item in received))
            self.assertGreaterEqual(len(self.nonzero("ovc")), 3)
            self.assertFalse(self.coyote.connected)
        finally:
            if legacy_phone is not None:
                await legacy_phone.close()
            if reader is not None:
                reader.cancel()
                with suppress(asyncio.CancelledError, websockets.ConnectionClosed):
                    await reader
            legacy._stop_event.set()
            await asyncio.wait_for(legacy_server, 3)

    async def test_events_are_role_tagged(self):
        await self.select("coyote")
        await self.select("ovc")
        events = []
        while not self.hub.events.empty():
            events.append(self.hub.events.get_nowait()[1])
        roles = {event.get("role") for event in events}
        self.assertTrue({"hub", "coyote", "ovc"}.issubset(roles))
        self.assertTrue(all(event.get("protocol") == "v4" for event in events))


if __name__ == "__main__":
    unittest.main()
