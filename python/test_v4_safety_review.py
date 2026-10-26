"""Independent V4 safety regressions; no sockets or physical output."""
import asyncio
from contextlib import suppress
import queue
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from manaka_devices.dglab_v4 import DGLabV4Bridge, channel_block_reason


def device(kind="OVC_1"):
    return {"slotId": "s1", "name": "review fake", "type": kind,
            "props": {"connectState": "connected", "channelAStatus": True,
                      "channelBStatus": False},
            "slotState": {"hasDevice": True, "channelA": {"isMuted": False},
                          "channelB": {"isMuted": False}}}


class V4ReadinessReviewTests(unittest.TestCase):
    def test_single_ovc_accessory_allows_only_that_channel(self):
        raw = device()
        self.assertEqual(channel_block_reason(raw, "A"), "")
        self.assertEqual(channel_block_reason(raw, "B"), "accessory-not-inserted")

    def test_electrical_zero_status_is_not_an_error(self):
        raw = device("COYOTE_030")
        for status in (0, 1, 2):
            raw["props"]["channelAStatus"] = status
            self.assertEqual(channel_block_reason(raw, "A"), "")
        for status in (3, 4):
            raw["props"]["channelAStatus"] = status
            self.assertEqual(channel_block_reason(raw, "A"), "channel-fault-or-blocked")

    def test_either_positive_bluetooth_signal_but_explicit_negative_wins(self):
        raw = device("COYOTE_030")
        raw["props"] = {}
        self.assertEqual(channel_block_reason(raw, "A"), "")
        raw["props"]["connectState"] = "disconnected"
        self.assertEqual(channel_block_reason(raw, "A"), "bluetooth-not-connected")
        raw["props"]["connectState"] = "connected"
        raw["slotState"]["hasDevice"] = False
        self.assertEqual(channel_block_reason(raw, "A"), "bluetooth-not-connected")

    def test_unknown_accessory_or_missing_link_never_authorizes(self):
        raw = device()
        raw["props"].pop("channelAStatus")
        self.assertEqual(channel_block_reason(raw, "A"), "accessory-not-inserted")
        raw["props"].pop("connectState")
        raw["slotState"].pop("hasDevice")
        self.assertEqual(channel_block_reason(raw, "A"), "bluetooth-not-connected")


class V4StateReviewTests(unittest.TestCase):
    def setUp(self):
        with patch("manaka_devices.dglab_bridge.ipv4_interfaces", return_value=[{"address": "127.0.0.1"}]):
            self.bridge = DGLabV4Bridge(queue.Queue())
        self.bridge._devices = {"app1": {"s1": device()}}

    def test_incremental_mute_merge_keeps_insertion_and_bluetooth(self):
        bridge = self.bridge
        bridge._handle_app_data("app1", {"t": "ev", "ev": "slots.patch", "slots": [
            {"slotId": "s1", "slotState": {"channelA": {"isMuted": True}}}]})
        raw = bridge._devices["app1"]["s1"]
        self.assertTrue(raw["slotState"]["hasDevice"])
        self.assertTrue(raw["props"]["channelAStatus"])
        self.assertEqual(channel_block_reason(raw, "A"), "channel-muted")
        bridge._handle_app_data("app1", {"t": "ev", "ev": "slots.patch", "slots": [
            {"slotId": "s1", "slotState": {"channelA": {"isMuted": False}}}]})
        self.assertEqual(channel_block_reason(bridge._devices["app1"]["s1"], "A"), "")

    def test_wrong_app_cannot_complete_another_apps_baseline(self):
        bridge = self.bridge
        future = MagicMock()
        future.done.return_value = False
        bridge._pending["request"] = {"client_id": "app1", "method": "device.op",
                                       "safety": True, "future": future}
        bridge._handle_app_data("app2", {"t": "resp", "reqId": "request",
                                        "result": {"reason": "completed", "type": 7}})
        self.assertFalse(future.done())
        self.assertIn("request", bridge._pending)
        future.set_result.assert_not_called()
        future.set_exception.assert_not_called()

    def test_public_state_is_an_independent_copy(self):
        bridge = self.bridge
        bridge._publish_devices()
        first = bridge.devices_snapshot()
        first[0]["props"]["channelAStatus"] = False
        second = bridge.devices_snapshot()
        self.assertTrue(second[0]["props"]["channelAStatus"])
        self.assertTrue(bridge._devices["app1"]["s1"]["props"]["channelAStatus"])


class V4WriteTimeoutReviewTests(unittest.IsolatedAsyncioTestCase):
    async def test_generation_is_rechecked_in_scheduled_write(self):
        with patch("manaka_devices.dglab_bridge.ipv4_interfaces", return_value=[{"address": "127.0.0.1"}]):
            bridge = DGLabV4Bridge(queue.Queue(), port=0)
        bridge._devices = {"app": {"s1": device()}}
        bridge.selected_client_id, bridge.selected_slot_id = "app", "s1"
        bridge.connected = bridge._baseline_ready = bridge._auto_enabled = True
        bridge._clients["app"] = websocket = MagicMock()
        websocket.send = AsyncMock()
        wait_for = asyncio.wait_for

        async def invalidate_before_task_runs(coro, timeout):
            bridge._generation += 1
            return await wait_for(coro, timeout)

        with patch("manaka_devices.dglab_v4.asyncio.wait_for", side_effect=invalidate_before_task_runs):
            written = await bridge._rpc("device.op", {"s": "s1", "c": 0, "t": 4, "v": 10})
        self.assertFalse(written)
        websocket.send.assert_not_awaited()
        self.assertEqual(bridge._pending, {})

    async def test_timeout_disarms_without_permanently_killing_output_worker(self):
        with patch("manaka_devices.dglab_bridge.ipv4_interfaces", return_value=[{"address": "127.0.0.1"}]):
            bridge = DGLabV4Bridge(queue.Queue())
        bridge._devices = {"app1": {"s1": device()}}
        bridge.selected_client_id, bridge.selected_slot_id = "app1", "s1"
        bridge.device_type = "OVC_1"
        bridge.connected = bridge._baseline_ready = True
        bridge._auto_enabled = True
        bridge._desired_strength = {"A": 10, "B": 0}
        bridge._desired_frames = {"A": ("0A0A0A0A32323232",), "B": ()}
        bridge._desired_updated_at = time.monotonic()

        async def blocked_write(_):
            await asyncio.sleep(10)

        websocket = MagicMock()
        websocket.send = AsyncMock(side_effect=blocked_write)
        websocket.close = AsyncMock()
        bridge._clients["app1"] = websocket
        with patch("manaka_devices.dglab_v4.SEND_TIMEOUT", .01):
            output = asyncio.create_task(bridge._output_loop())
            try:
                await asyncio.sleep(.09)
                self.assertFalse(bridge.connected)
                self.assertFalse(bridge._auto_enabled)
                self.assertFalse(output.done(), "Reconnect must not inherit a dead output worker")
                self.assertEqual(bridge._desired_updated_at, 0)
                # A slow host may observe the bounded safety-zero transaction
                # between its concurrent writes. It must still finish promptly.
                deadline = time.monotonic() + .5
                while bridge._pending and time.monotonic() < deadline:
                    await asyncio.sleep(.005)
                self.assertEqual(bridge._pending, {})
            finally:
                output.cancel()
                with suppress(asyncio.CancelledError):
                    await output


if __name__ == "__main__":
    unittest.main()
