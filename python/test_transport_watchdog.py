import asyncio
import json
import queue
import threading
import time
import unittest

from manaka_dglab_bridge import DGLabBridge


class TransportWatchdogTests(unittest.TestCase):
    def test_pre_pause_updates_cannot_resume_a_previous_event(self):
        bridge = DGLabBridge(queue.Queue(), port=0)
        generation = bridge._generation
        bridge._generation += 1
        bridge._set_desired_outputs_in_loop(20, ("0A0A0A0A14141414",), "old-event", 0, (), "off", 30,
            generation=generation)
        self.assertEqual(bridge._desired_strength["A"], 0)

    def test_full_once_stream_and_other_channel_loop_without_replaying_tail(self):
        async def scenario():
            bridge = DGLabBridge(queue.Queue(), port=0)
            bridge.connected = bridge._auto_enabled = True
            bridge._loop = asyncio.get_running_loop()
            bridge.telemetry_timeout = 10
            frames = tuple(f"0A0A0A0A{x:02X}{x:02X}{x:02X}{x:02X}" for x in range(23))
            sent = []
            async def send(message):
                sent.append(message)
                return True
            bridge._send_message = send
            bridge._set_desired_outputs_in_loop(10, frames, "once-A", 10, (frames[0],), "loop-B", 30, loop_a=False)
            task = asyncio.create_task(bridge._output_loop())
            try:
                await asyncio.sleep(2.9)
                actual = [frame for message in sent if message.startswith("pulse-A:") for frame in json.loads(message.split(":",1)[1])]
                self.assertEqual(actual, list(frames))
                self.assertIn("strength-1+2+0", sent)
                self.assertEqual(bridge.playback_state["A"], ("once-A", "finished"))
                self.assertGreater(sum(message.startswith("pulse-B:") for message in sent), 8)
                self.assertTrue(all(len(json.loads(message.split(":",1)[1])) <= 3 for message in sent if message.startswith("pulse-")))
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
        asyncio.run(scenario())

    def test_cap_decrease_while_clear_is_awaited_is_applied_before_strength(self):
        async def scenario():
            bridge = DGLabBridge(queue.Queue(), port=0)
            bridge.connected = bridge._auto_enabled = True
            bridge._loop = asyncio.get_running_loop()
            sent = []
            async def send(message):
                sent.append(message)
                if message == "clear-1":
                    bridge._device_limits["A"] = 2
                return True
            bridge._send_message = send
            bridge._set_desired_outputs_in_loop(10, ("0A0A0A0A14141414",), "A", 0, (), "B", 30)
            task = asyncio.create_task(bridge._output_loop())
            try:
                await asyncio.sleep(.08)
                self.assertIn("strength-1+2+2", sent)
                self.assertNotIn("strength-1+2+10", sent)
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
        asyncio.run(scenario())

    def test_invalid_frame_after_first_hundred_is_rejected_before_enqueue(self):
        bridge = DGLabBridge(queue.Queue(), port=0)
        with self.assertRaises(ValueError):
            bridge.update_auto_outputs(10, ["0A0A0A0A14141414"]*100+["FFFFFFFFFFFFFFFF"],
                wave_key_a="bad", strength_b=0, frames_b=(), wave_key_b="off", hard_cap=30)

    def test_manual_test_obeys_configured_channel_cap_before_first_telemetry(self):
        async def scenario():
            bridge = DGLabBridge(queue.Queue(),port=0)
            bridge.configure_limits(30,3,5)
            bridge.connected = True
            bridge._loop = asyncio.get_running_loop()
            sent = []
            async def send(message):
                sent.append(message)
                return True
            bridge._send_message = send
            self.assertTrue(bridge.manual_test(10,["0A0A0A0A14141414"],hard_cap=30))
            await asyncio.sleep(.04)
            self.assertIn("strength-1+2+3",sent)
            self.assertNotIn("strength-1+2+10",sent)
            bridge._request_emergency_in_loop()
            await asyncio.sleep(.2)
        asyncio.run(scenario())

    def test_watchdog_and_device_limits_run_without_any_gui_poll(self):
        async def scenario():
            bridge = DGLabBridge(queue.Queue(), port=0)
            bridge.connected = True
            bridge._auto_enabled = True
            bridge._loop = asyncio.get_running_loop()
            bridge.telemetry_timeout = .2
            bridge._device_limits = {"A": 4, "B": 9}
            sent = []
            async def send(message):
                sent.append((time.monotonic(), message))
                return True
            bridge._send_message = send
            now = time.monotonic()
            bridge._set_desired_outputs_in_loop(80, ("0A0A0A0A14141414",), "test", 80,
                ("0A0A0A0A14141414",), "test", 90, now, 6, 7)
            task = asyncio.create_task(bridge._output_loop())
            try:
                # This loop owns both transport and watchdog; no Qt event loop exists.
                await asyncio.sleep(.7)
                messages = [message for _, message in sent]
                self.assertIn("strength-1+2+4", messages)
                self.assertIn("strength-2+2+7", messages)
                self.assertIn("strength-1+2+0", messages)
                self.assertIn("strength-2+2+0", messages)
                first_zero = next(stamp for stamp, message in sent if message == "strength-1+2+0")
                self.assertLess(first_zero-now, .6)
                self.assertNotIn("pulse-B:[\"0A0A0A0A14141414\"]", messages)
                # Old buffered data must not refresh freshness or resume output.
                bridge._set_desired_outputs_in_loop(80, (), "test", 80, (), "test", 90, now-1, 90, 90)
                self.assertEqual(bridge._desired_strength, {"A":0,"B":0})
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
        asyncio.run(scenario())

    def test_emergency_during_clear_gap_cannot_send_a_stale_wave(self):
        async def scenario():
            bridge = DGLabBridge(queue.Queue(), port=0)
            bridge.connected = bridge._auto_enabled = True
            bridge._loop = asyncio.get_running_loop()
            sent = []
            async def send(message):
                sent.append(message)
                return True
            bridge._send_message = send
            bridge._set_desired_outputs_in_loop(10, ("0A0A0A0A14141414",), "test", 10,
                ("0A0A0A0A14141414",), "test", 30)
            task = asyncio.create_task(bridge._output_loop())
            try:
                await asyncio.sleep(.08)
                bridge._request_emergency_in_loop()
                await asyncio.sleep(.3)
                self.assertFalse(any(message.startswith("pulse-") for message in sent))
                self.assertIn("strength-1+2+0", sent)
                self.assertIn("strength-2+2+0", sent)
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
        asyncio.run(scenario())
