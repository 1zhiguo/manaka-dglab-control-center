"""Coyote 2.0 V4 transport checks using in-memory APP replies only."""
import asyncio
import json
import math
import queue
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from manaka_devices.device_types import COYOTE_TYPES, OVC_TYPES
from manaka_devices.dglab_v4 import DGLabV4Bridge, channel_block_reason, channel_intensity_limit
from manaka_devices.dglab_v4_hub import ROLE_TYPES


def coyote(kind="COYOTE_020"):
    # Hardware 2.0 does not expose 3.0 circuit status fields.
    return {"slotId": "coyote", "type": kind,
            "props": {"connectState": "connected"},
            "slotState": {"hasDevice": True,
                "channelA": {"isMuted": False, "intensityMax": 40, "intensityMaxMax": 100},
                "channelB": {"isMuted": False, "intensityMax": 50, "intensityMaxMax": 100}}}


def bridge_with_device(raw):
    with patch("manaka_devices.dglab_bridge.ipv4_interfaces", return_value=[{"address": "127.0.0.1"}]):
        bridge = DGLabV4Bridge(queue.Queue(), port=0, host="127.0.0.1")
    bridge._devices = {"mock": {"coyote": raw}}
    bridge.selected_client_id = "mock"
    bridge.selected_slot_id = "coyote"
    bridge.device_type = raw["type"]
    bridge._hard_cap = 60
    bridge._desired_strength = {"A": 55, "B": 45}
    return bridge


class CoyoteCapabilities(unittest.TestCase):
    def test_hardware_roles_are_independent_of_socket_generation(self):
        self.assertEqual(COYOTE_TYPES, {"COYOTE_020", "COYOTE_030"})
        self.assertEqual(ROLE_TYPES["coyote"], COYOTE_TYPES)
        self.assertEqual(ROLE_TYPES["ovc"], OVC_TYPES)
        self.assertFalse(COYOTE_TYPES & OVC_TYPES)

    def test_020_without_030_circuit_fields_is_ready(self):
        raw = coyote()
        self.assertNotIn("channelAStatus", raw["props"])
        self.assertEqual(channel_block_reason(raw, "A"), "")
        self.assertEqual(channel_block_reason(raw, "B"), "")
        raw["props"]["channelAStatus"] = 3
        self.assertEqual(channel_block_reason(raw, "A"), "")
        raw["type"] = "COYOTE_030"
        self.assertEqual(channel_block_reason(raw, "A"), "channel-fault-or-blocked")

    def test_bluetooth_and_mute_signals_still_apply_to_020(self):
        raw = coyote()
        raw["slotState"]["channelB"]["isMuted"] = True
        self.assertEqual(channel_block_reason(raw, "B"), "channel-muted")
        raw["slotState"]["hasDevice"] = False
        self.assertEqual(channel_block_reason(raw, "A"), "bluetooth-not-connected")

    def test_current_cap_not_growth_ceiling_is_used(self):
        raw = coyote()
        bridge = bridge_with_device(raw)
        self.assertEqual(bridge._channel_strength("A"), 40)
        self.assertEqual(bridge._channel_strength("B"), 45)
        raw["slotState"]["channelA"]["intensityMax"] = 12
        self.assertEqual(bridge._channel_strength("A"), 12)
        raw["slotState"]["channelA"]["intensityMax"] = 0
        self.assertEqual(bridge._channel_strength("A"), 0)
        raw["slotState"]["channelA"].pop("intensityMax")
        self.assertIsNone(channel_intensity_limit(raw, "A"))
        self.assertEqual(bridge._channel_strength("A"), 0)
        self.assertEqual(bridge._channel_strength("B"), 45)

    def test_invalid_current_caps_fail_closed_for_both_coyotes(self):
        for kind in COYOTE_TYPES:
            raw = coyote(kind)
            bridge = bridge_with_device(raw)
            for invalid in (None, True, False, "50", -1, float("nan"), float("inf"), {}, []):
                with self.subTest(kind=kind, invalid=repr(invalid)):
                    raw["slotState"]["channelA"]["intensityMax"] = invalid
                    self.assertEqual(bridge._channel_strength("A"), 0)
                    self.assertEqual(bridge._channel_strength("B"), 45)

    def test_policy_user_cap_app_cap_and_protocol_ceiling_all_apply(self):
        raw = coyote()
        bridge = bridge_with_device(raw)
        for target, user, app, expected in ((55, 60, 40, 40), (55, 20, 40, 20),
                                          (12, 20, 40, 12), (180, 200, 200, 100)):
            bridge._desired_strength["A"] = target
            bridge._hard_cap = user
            raw["slotState"]["channelA"]["intensityMax"] = app
            self.assertEqual(bridge._channel_strength("A"), expected)

    def test_coyote_frames_cannot_be_relabelled_short_v2_frames(self):
        bridge = bridge_with_device(coyote())
        for frame in ("0A0A", "00" * 16):
            with self.subTest(frame=frame), self.assertRaises(ValueError):
                bridge.update_auto_outputs(10, [frame], wave_key_a="bad", strength_b=0,
                    frames_b=[], wave_key_b="off", hard_cap=30)


class QueuedProducer(unittest.TestCase):
    def setUp(self):
        self.bridge = bridge_with_device(coyote())
        self.bridge._loop = MagicMock()

    def queue(self):
        self.bridge.update_auto_outputs(35, ["3232323264646464"], wave_key_a="old-a",
            strength_b=20, frames_b=["1111111132323232"], wave_key_b="old-b", hard_cap=60)
        callback, *values = self.bridge._loop.call_soon_threadsafe.call_args.args
        return callback, values

    def test_preselection_callback_cannot_refresh_a_new_session(self):
        callback, values = self.queue()
        self.bridge._selection_epoch += 1
        self.bridge._discard_outputs()
        callback(*values)
        self.assertEqual(self.bridge._desired_updated_at, 0)
        self.assertEqual(self.bridge._desired_strength, {"A": 0, "B": 0})

    def test_preemergency_and_prepause_callbacks_are_discarded(self):
        for field in ("_generation", "_pause_epoch"):
            callback, values = self.queue()
            setattr(self.bridge, field, getattr(self.bridge, field) + 1)
            self.bridge._desired_updated_at = 0
            callback(*values)
            self.assertEqual(self.bridge._desired_updated_at, 0)

    def test_expired_producer_plan_does_not_get_a_new_timestamp(self):
        with patch("manaka_devices.dglab_v4.time.monotonic", return_value=100):
            callback, values = self.queue()
        with patch("manaka_devices.dglab_v4.time.monotonic", return_value=100.6):
            callback(*values)
        self.assertEqual(self.bridge._desired_updated_at, 0)

    def test_fresh_plan_keeps_its_production_time(self):
        with patch("manaka_devices.dglab_v4.time.monotonic", return_value=100):
            callback, values = self.queue()
        with patch("manaka_devices.dglab_v4.time.monotonic", return_value=100.3):
            callback(*values)
        self.assertEqual(self.bridge._desired_updated_at, 100)
        self.assertEqual(self.bridge._desired_strength, {"A": 35, "B": 20})

    def test_queued_enable_cannot_rearm_a_replaced_session(self):
        self.bridge.connected = self.bridge._baseline_ready = True
        self.bridge.set_auto_enabled(True)
        callback = self.bridge._loop.call_soon_threadsafe.call_args.args[0]
        self.bridge._selection_epoch += 1
        self.bridge._discard_outputs()
        self.bridge._desired_updated_at = time.monotonic()
        callback()
        self.assertFalse(self.bridge._auto_enabled)


class CoyoteOutput(unittest.IsolatedAsyncioTestCase):
    async def test_fast_single_channel_mute_edge_cannot_skip_clear(self):
        raw = coyote()
        bridge = bridge_with_device(raw)
        bridge.connected = bridge._baseline_ready = bridge._auto_enabled = True
        bridge._clients["mock"] = MagicMock()
        bridge._previous_channel_reasons = {"A": "", "B": ""}
        with patch.object(bridge, "_start_channel_zero") as clear:
            raw["slotState"]["channelA"]["isMuted"] = True
            bridge._check_selected()
            raw["slotState"]["channelA"]["isMuted"] = False
            bridge._check_selected()
            clear.assert_called_once_with("mock", "coyote", 0)
        self.assertTrue(bridge.connected)
        self.assertEqual(bridge._desired_strength, {"A": 0, "B": 45})

    async def test_scheduled_write_rechecks_new_channel_zero_barrier(self):
        bridge = bridge_with_device(coyote())
        bridge.connected = bridge._baseline_ready = bridge._auto_enabled = True
        socket = MagicMock()
        socket.send = AsyncMock()
        bridge._clients["mock"] = socket
        original_wait = asyncio.wait_for
        barrier = asyncio.get_running_loop().create_future()
        async def barrier_before_send(coro, timeout):
            bridge._channel_zero_transactions[("mock", "coyote", 0)] = barrier
            return await original_wait(coro, timeout)
        try:
            with patch("manaka_devices.dglab_v4.asyncio.wait_for", side_effect=barrier_before_send):
                self.assertFalse(await bridge._rpc("device.op", {"s": "coyote", "c": 0, "t": 4, "v": 20}))
            socket.send.assert_not_awaited()
        finally:
            barrier.cancel()

    async def test_scheduled_write_rechecks_current_app_limit(self):
        raw = coyote()
        bridge = bridge_with_device(raw)
        bridge.connected = bridge._baseline_ready = bridge._auto_enabled = True
        socket = MagicMock()
        socket.send = AsyncMock()
        bridge._clients["mock"] = socket
        original_wait = asyncio.wait_for

        async def lowered_before_send(coro, timeout):
            raw["slotState"]["channelA"]["intensityMax"] = 7
            return await original_wait(coro, timeout)

        with patch("manaka_devices.dglab_v4.asyncio.wait_for", side_effect=lowered_before_send):
            self.assertTrue(await bridge._rpc("device.op", {"s": "coyote", "c": 0, "t": 4, "v": 40}))
        wire = json.loads(socket.send.call_args.args[0])
        self.assertEqual(wire["data"]["data"]["v"], 7)

    async def test_missing_or_zero_cap_blocks_even_a_preplanned_write(self):
        for maximum in (None, 0, True, float("nan"), -1):
            raw = coyote()
            raw["slotState"]["channelA"]["intensityMax"] = maximum
            bridge = bridge_with_device(raw)
            bridge.connected = bridge._baseline_ready = bridge._auto_enabled = True
            socket = MagicMock()
            socket.send = AsyncMock()
            bridge._clients["mock"] = socket
            self.assertFalse(await bridge._rpc("device.op", {"s": "coyote", "c": 0, "t": 4, "v": 10}))
            socket.send.assert_not_awaited()
            self.assertEqual(bridge._pending, {})

    async def test_ab_stream_has_independent_v3_frames_and_short_leases(self):
        raw = coyote()
        bridge = bridge_with_device(raw)
        bridge.connected = bridge._baseline_ready = bridge._auto_enabled = True
        bridge._desired_frames = {"A": ("3232323264646464", "3333333350505050"),
                                  "B": ("1111111132323232",)}
        bridge._desired_wave_key = {"A": "a", "B": "b"}
        bridge._desired_updated_at = time.monotonic()
        rows = []
        socket = MagicMock()

        async def send(payload):
            request = json.loads(payload)["data"]
            rows.append(request)
            data = request.get("data", {})
            bridge._handle_app_data("mock", {"t": "resp", "reqId": request["reqId"],
                "result": {"type": data.get("t"), "reason": "completed",
                           "slotId": data.get("s"), "channel": data.get("c")}})

        socket.send = AsyncMock(side_effect=send)
        bridge._clients["mock"] = socket
        worker = asyncio.create_task(bridge._output_loop())
        try:
            await asyncio.sleep(.27)
        finally:
            # Let an immediate mocked reply leave wait_for before cancelling.
            # No real socket/driver exists in this in-memory test.
            bridge._auto_enabled = False
            await asyncio.sleep(.04)
            worker.cancel()
            await asyncio.wait_for(asyncio.gather(worker, return_exceptions=True), 1)
        pulses = [r["data"] for r in rows if r["data"]["t"] == 0]
        strengths = [r["data"] for r in rows if r["data"]["t"] == 4]
        self.assertGreaterEqual(len(pulses), 4)
        self.assertEqual({p["c"] for p in pulses}, {0, 1})
        self.assertTrue(all(p["ver"] == 3 and p["d"] == 100 and len(p["v"]) == 1
                            and len(p["v"][0]) == 16 and p["im"] for p in pulses))
        self.assertEqual({p["v"][0] for p in pulses if p["c"] == 0},
                         {"3232323264646464", "3333333350505050"})
        self.assertEqual({p["v"][0] for p in pulses if p["c"] == 1}, {"1111111132323232"})
        self.assertTrue(all(s["d"] == 300 and s["im"] for s in strengths))
        self.assertEqual({s["v"] for s in strengths if s["c"] == 0}, {40})
        self.assertEqual({s["v"] for s in strengths if s["c"] == 1}, {45})


if __name__ == "__main__":
    unittest.main()
