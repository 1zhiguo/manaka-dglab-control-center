"""Source and packaged-EXE Coyote 2.0 verification, using loopback only.

The real Manaka backend, planners and background V4 workers run against a fake
APP. Game packets are fixtures, not game reads. No Bluetooth route is present.
"""
from __future__ import annotations

import asyncio
from contextlib import ExitStack
from copy import deepcopy
import io
import json
import math
from pathlib import Path
import queue
import sys
import tempfile
import time
import traceback
import unittest
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication

from .dglab_v4_hub import DGLabV4Hub
from .mock_v4 import MockV4App, mock_device
from .ovc import sanitize_profile
from qml_dashboard_prototype import backend as backend_module


EVIDENCE: list[dict] = []
FRAME_A = ("0A0A0A0A64322814", "0B0B0B0B14322864", "0C0C0C0C28282828")
FRAME_B = ("1414141410101010", "1515151520202020")


def game_packet(**changes) -> dict:
    value = dict(sequence=1, monotonicMs=10000, heartRate=160.0,
                 stage="Residence", action="SexStandBack", playingAction=True,
                 maxNpcAlert=0., risingNpcCount=0, watchingNpcCount=0,
                 ecstasy=.5, orgasm=False, gameOver=False, vibration="High")
    value.update(changes)
    return value


class Coyote2ScenarioTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QCoreApplication.instance() or QCoreApplication([])

    async def asyncSetUp(self):
        asyncio.get_running_loop().set_debug(False)
        self.temp = tempfile.TemporaryDirectory(prefix="manaka-coyote2-loopback-")
        self.context = ExitStack()
        directory = Path(self.temp.name)
        self.context.enter_context(patch.object(backend_module, "load_config", return_value={
            "language": "en", "socket_protocol": "v4", "hard_cap": 60,
            "output_max": 60, "min_strength": 5, "trigger_bpm": 90, "full_bpm": 160}))
        self.context.enter_context(patch.object(backend_module, "app_data_dir", return_value=directory))
        self.context.enter_context(patch.object(backend_module, "waveform_library_dir", return_value=directory / "waves"))
        self.context.enter_context(patch.object(backend_module, "dropin_mods_path", return_value=directory / "dropin"))
        self.context.enter_context(patch.object(backend_module, "update_config"))
        self.context.enter_context(patch.object(backend_module.device_audit, "record"))
        self.context.enter_context(patch("manaka_devices.dglab_bridge.ipv4_interfaces", return_value=[{"address": "127.0.0.1"}]))
        self.b = backend_module.ControlCenterBackend(demo=True, language="en")
        self.b.poll_timer.stop()
        self.b.demo_mode = False
        self.b.auto_output_enabled = self.b.device_connected_value = self.b.ovc_connected = False
        self.b.socket_protocol = "v4"
        self.b.last_packet, self.b.last_receive = {}, 0.
        self.b._device_persist = lambda value: None
        self.hub = DGLabV4Hub(self.b.v4_messages, host="127.0.0.1", port=0, lan_ip="127.0.0.1")
        self.b.v4_hub = self.hub
        self.route = self.hub.channel("coyote")
        self.ovc = self.hub.channel("ovc")
        self.b.bridge = self.route
        self.app = MockV4App(coyote_type="COYOTE_020")
        self.packet = game_packet()
        self.game_ms = 10000
        self.target = (55, 65, 60)
        self.hub.start()
        await self.until(lambda: self.hub.server_ready)
        self.assertEqual({s.getsockname()[0] for s in self.hub._server.sockets}, {"127.0.0.1"})

    async def asyncTearDown(self):
        try:
            if self.hub._thread and self.hub._thread.is_alive():
                await asyncio.to_thread(self.hub.stop)
            await self.app.close()
            EVIDENCE.append({"case": self._testMethodName,
                             "physical_hardware_connected": False,
                             "listen_host": "127.0.0.1", "listen_port": self.hub.port,
                             "requests": self.app.records, "completions": self.app.responses,
                             "mock_rejections": self.app.errors})
        finally:
            self.b.v4_hub = self.b.bridge = None
            self.b.shutdown()
            self.context.close()
            self.temp.cleanup()

    def pump(self):
        self.b._poll_device_support()
        while not self.b.messages.empty():
            kind, payload = self.b.messages.get_nowait()
            if kind == "dglab":
                self.b._handle_dglab_event(payload)
        self.qt.processEvents()

    def feed(self, **changes):
        self.packet.update(changes)
        self.game_ms += 100
        self.b._on_telemetry({**self.packet, "sequence": self.game_ms,
                              "monotonicMs": self.game_ms,
                              "_received_monotonic": time.monotonic()})
        self.b._sync_ovc(force=True)

    def wire_plan(self):
        a, b, cap = self.target
        self.route.update_auto_outputs(a, FRAME_A, wave_key_a="validation-a",
                                       strength_b=b, frames_b=FRAME_B,
                                       wave_key_b="validation-b", hard_cap=cap)

    async def until(self, fn, seconds=3., *, wire=False, game=False):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.pump()
            if wire:
                self.wire_plan()
            if game:
                self.feed()
            if fn():
                return
            await asyncio.sleep(.015)
        self.fail("Loopback condition timed out: " + getattr(fn, "__name__", "predicate")
                  + "; connected=" + str(self.route.connected)
                  + "; status=" + str(self.b.device_status_value)
                  + "; errors=" + repr(self.app.errors))

    async def drive(self, seconds=.2, *, wire=False, game=False):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.pump()
            if wire:
                self.wire_plan()
            if game:
                self.feed()
            await asyncio.sleep(.025)

    async def connect(self):
        await self.app.connect(f"ws://127.0.0.1:{self.hub.port}/?tid={self.hub.controller_id}")
        await self.until(lambda: len(self.hub.devices_snapshot()) == 2)

    async def ready(self):
        await self.connect()
        await self.until(lambda: self.route.connected and self.ovc.connected and self.b.device_connected_value and self.b.ovc_connected)
        self.assertEqual(self.route.device_type, "COYOTE_020")
        self.assertFalse(self.b.auto_output_enabled or self.route._auto_enabled)

    async def arm_wire(self):
        self.wire_plan()
        self.route.set_auto_enabled(True)
        await self.until(lambda: self.route._auto_enabled, wire=True)
        await self.until(lambda: bool(self.app.strengths()), wire=True)

    async def arm_backend(self):
        self.b.ovc_profile = sanitize_profile({
            "mode": "independent", "hard_cap": 80,
            "channels": {"A": {"enabled": True, "mode": "fixed", "wave": "ovc_pulse", "strength": 40},
                         "B": {"enabled": True, "mode": "fixed", "wave": "ovc_ramp", "strength": 50}}})
        self.feed()
        self.b.toggleOutput()
        self.b.toggleOvcOutput()
        await self.until(lambda: self.route._auto_enabled and self.ovc._auto_enabled, game=True)
        await self.until(lambda: bool(self.app.strengths()) and bool(self.app.strengths("ovc")), game=True)

    def assert_no_nonzero(self, *, since, slot="coyote", first_record_index=0):
        rows = [r for r in self.app.records[first_record_index:]
                if r["at"] >= since and r.get("m") == "device.op"
                and (r.get("data") or {}).get("s") == slot]
        self.assertFalse([r for r in rows if r["data"]["t"] == 4 and r["data"]["v"] > 0])
        self.assertFalse([r for r in rows if r["data"]["t"] == 0])

    def assert_barrier_before_output(self, since=0, *, first_record_index=0):
        rows = [r for r in self.app.records[first_record_index:] if r["at"] >= since and (r.get("data") or {}).get("s") == "coyote"]
        first = next((i for i, r in enumerate(rows) if r["m"] == "device.op" and r["data"]["t"] in {0, 4}), len(rows))
        prefix = rows[:first]
        methods = [(r["m"], r.get("data", {}).get("t")) for r in prefix]
        self.assertIn(("device.op.clear", None), methods)
        clear = next(i for i, r in enumerate(prefix) if r["m"] == "device.op.clear")
        before = [r for r in prefix[:clear] if r["m"] == "device.op" and r["data"]["t"] == 7]
        after = [r for r in prefix[clear + 1:] if r["m"] == "device.op" and r["data"]["t"] == 7]
        self.assertEqual({r["data"]["c"] for r in before}, {0, 1})
        self.assertEqual({r["data"]["c"] for r in after}, {0, 1})
        replies = {r["reqId"]: r for r in self.app.responses}
        for r in before + after:
            self.assertEqual(replies[r["reqId"]]["result"]["reason"], "completed")
        self.assertLessEqual(max(replies[r["reqId"]]["at"] for r in before), prefix[clear]["at"])
        self.assertLessEqual(replies[prefix[clear]["reqId"]]["at"], min(r["at"] for r in after))
        if first < len(rows):
            self.assertLessEqual(max(replies[r["reqId"]]["at"] for r in after), rows[first]["at"])

    async def test_01_discovery_ui_choices_wait_for_all_three_completion_phases(self):
        self.app.hold_zero = True
        await self.connect()
        await self.until(lambda: len(self.app.held) == 2)
        rows = self.hub.devices_snapshot()
        coyote = next(r for r in rows if r["type"] == "COYOTE_020")
        self.assertNotIn("channelAStatus", coyote["props"])
        self.assertNotIn("channelBStatus", coyote["props"])
        self.assertTrue(any(r.get("slotId") == "coyote" for r in self.b.coyoteDevices))
        self.assertFalse(any(r.get("slotId") == "ovc" for r in self.b.coyoteDevices))
        self.assertFalse(self.hub.select_device("ovc", self.app.client_id, "coyote"))
        self.assertFalse(self.hub.select_device("coyote", self.app.client_id, "ovc"))
        self.b.toggleOutput()
        self.assertFalse(self.b.auto_output_enabled or self.route.connected)
        self.app.hold_zero, self.app.hold_clear = False, True
        await self.app.release_held()
        await self.until(lambda: len(self.app.held) == 1 and self.app.held[0]["m"] == "device.op.clear")
        self.assertFalse(self.route.connected)
        self.app.hold_zero, self.app.hold_clear = True, False
        await self.app.release_held()
        await self.until(lambda: len(self.app.held) == 2)
        self.assertFalse(self.route.connected)
        self.assertEqual(len(self.app.tasks(task_type=7)), 4)
        self.app.hold_zero = False
        await self.app.release_held()
        await self.until(lambda: self.route.connected and self.b.device_connected_value)
        self.assertFalse(self.b.auto_output_enabled or self.route._auto_enabled)
        await self.arm_wire()
        self.assert_barrier_before_output()
        self.assertFalse(self.app.errors)

    async def test_02_independent_ab_loop_queues_ver3_and_short_leases(self):
        await self.ready()
        await self.arm_wire()
        await self.drive(.85, wire=True)
        for channel, expected in (("A", FRAME_A), ("B", FRAME_B)):
            rows = self.app.pulses(channel=channel)
            self.assertGreaterEqual(len(rows), 5)
            frames = [r["data"]["v"][0] for r in rows]
            self.assertEqual(frames[:5], [expected[i % len(expected)] for i in range(5)])
            self.assertTrue(all(r["data"]["ver"] == 3 and r["data"]["d"] == 100 for r in rows))
            self.assertTrue(all(len(frame) == 16 for frame in frames))
        self.assertNotEqual(self.app.pulses(channel="A")[0]["data"]["v"], self.app.pulses(channel="B")[0]["data"]["v"])
        self.assertTrue(all(r["data"]["d"] == 300 and r["data"]["im"] for r in self.app.strengths()))
        self.assertTrue(all(r["data"]["v"] <= 60 for r in self.app.strengths()))
        self.assert_barrier_before_output()
        self.assertFalse(self.app.errors)

    async def test_03_dynamic_current_limits_zero_missing_invalid_and_no_growth_cap_fallback(self):
        self.app.devices[0]["slotState"]["channelA"]["intensityMax"] = 40
        self.app.devices[0]["slotState"]["channelB"]["intensityMax"] = 58
        await self.ready()
        await self.arm_wire()
        await self.drive(.2, wire=True)
        self.assertEqual(self.app.strengths(channel="A")[-1]["data"]["v"], 40)
        self.assertEqual(self.app.strengths(channel="B")[-1]["data"]["v"], 58)
        await self.app.patch_slot("coyote", slotState={"channelA": {"intensityMax": 12}, "channelB": {"intensityMax": 8}})
        await self.drive(.22, wire=True)
        self.assertEqual(self.app.strengths(channel="A")[-1]["data"]["v"], 12)
        self.assertEqual(self.app.strengths(channel="B")[-1]["data"]["v"], 8)
        for value in (0, None, -1, "100", True, float("nan"), float("inf")):
            await self.app.patch_slot("coyote", slotState={"channelA": {"intensityMax": value, "intensityMaxMax": 100}})
            await self.drive(.12, wire=True)
            since = time.monotonic()
            await self.drive(.14, wire=True)
            self.assertFalse([r for r in self.app.strengths(channel="A", since=since) if r["data"]["v"] > 0], repr(value))
            self.assertFalse(self.app.pulses(channel="A", since=since), repr(value))
            self.assertTrue(self.app.pulses(channel="B", since=since), repr(value))
        self.app.devices[0]["slotState"]["channelA"].pop("intensityMax")
        self.app.devices[0]["props"]["intensityMaxA"] = 100
        await self.app.snapshot()
        await self.drive(.12, wire=True)
        since = time.monotonic()
        await self.drive(.14, wire=True)
        self.assertFalse(self.app.pulses(channel="A", since=since))
        self.assertTrue(self.app.pulses(channel="B", since=since))
        self.assertFalse(self.app.errors)

    async def test_04_missing_both_limits_cannot_enable(self):
        for channel in ("A", "B"):
            self.app.devices[0]["slotState"]["channel" + channel].pop("intensityMax")
        await self.ready()
        self.assertTrue(self.b.deviceBlockReason("coyote"))
        self.b.toggleOutput()
        self.assertFalse(self.b.auto_output_enabled)
        await self.drive(.15, game=True)
        self.assertFalse(self.app.strengths() or self.app.pulses())

    async def test_05_single_double_mute_recovery_and_fresh_authorization(self):
        await self.ready()
        await self.arm_wire()
        await self.app.patch_slot("coyote", slotState={"channelA": {"isMuted": True}})
        await self.drive(.15, wire=True)
        since = time.monotonic()
        await self.drive(.2, wire=True)
        self.assertFalse(self.app.pulses(channel="A", since=since))
        self.assertTrue(self.app.pulses(channel="B", since=since))
        self.assertTrue(self.route.connected)
        await self.app.patch_slot("coyote", slotState={"channelB": {"isMuted": True}})
        await self.until(lambda: not self.route.connected)
        await self.drive(.15)
        since = time.monotonic()
        await self.drive(.2)
        self.assert_no_nonzero(since=since)
        await self.app.patch_slot("coyote", slotState={"channelA": {"isMuted": False}, "channelB": {"isMuted": False}})
        await self.until(lambda: self.route.connected)
        await self.drive(.12)
        self.assert_no_nonzero(since=since)
        self.assertFalse(self.route._auto_enabled)
        await self.arm_wire()
        self.assert_barrier_before_output(since)
        self.assertFalse(self.app.errors)

    async def test_06_bluetooth_reconnect_discards_old_plan_and_rezeros(self):
        await self.ready()
        await self.arm_wire()
        await self.app.patch_slot("coyote", props={"connectState": "disconnected"}, slotState={"hasDevice": False})
        await self.until(lambda: not self.route.connected)
        await self.drive(.08)
        since = time.monotonic()
        await self.app.patch_slot("coyote", props={"connectState": "connected"}, slotState={"hasDevice": True})
        await self.until(lambda: self.route.connected)
        await self.drive(.15, game=True)
        self.assertFalse(self.route._auto_enabled or self.b.auto_output_enabled)
        self.assert_no_nonzero(since=since)
        self.assertEqual(self.route._desired_frames, {"A": (), "B": ()})
        await self.arm_wire()
        self.assert_barrier_before_output(since)
        self.assertFalse(self.app.errors)

    async def test_07_app_reconnect_and_late_old_completion_cannot_restore_plan(self):
        await self.ready()
        await self.arm_wire()
        self.app.hold_output = True
        await self.drive(.13, wire=True)
        old_requests = list(self.app.held)
        self.assertTrue(old_requests)
        await self.app.close()
        await self.until(lambda: not self.route.connected and not self.hub.app_connected)
        since = time.monotonic()
        # The reader has been drained by close(). Windows monotonic timestamps
        # can share a 15 ms tick across this boundary: retain receipt order too.
        first_record_index = len(self.app.records)
        self.app.hold_output = False
        self.app.held.clear()
        await self.connect()
        await self.until(lambda: self.route.connected)
        for r in old_requests:
            d = r["data"]
            await self.app.send({"t": "resp", "reqId": r["reqId"], "result": {"type": d["t"], "slotId": d["s"], "channel": d["c"], "reason": "completed"}})
        await self.drive(.12, game=True)
        self.assertFalse(self.route._auto_enabled or self.b.auto_output_enabled)
        self.assert_no_nonzero(since=since, first_record_index=first_record_index)
        await self.arm_wire()
        self.assert_barrier_before_output(since, first_record_index=first_record_index)
        self.assertFalse(self.app.errors)

    async def test_08_manual_pause_estop_unlock_and_background_output(self):
        await self.ready()
        await self.arm_backend()
        # Stop UI/backend pumping briefly: the dedicated sender continues using
        # the fresh plan, with APP completion handling in its own event loop.
        self.feed()
        since = time.monotonic()
        await asyncio.sleep(.22)
        self.assertTrue(self.app.pulses(since=since))
        self.b.toggleOutput()
        await self.drive(.18, game=True)
        since = time.monotonic()
        await self.drive(.16, game=True)
        self.assertFalse(self.b.auto_output_enabled)
        self.assert_no_nonzero(since=since)
        self.assertTrue(self.app.pulses("ovc", since=since))
        await self.app.patch_slot("coyote", props={"connectState": "disconnected"}, slotState={"hasDevice": False})
        await self.until(lambda: not self.route.connected)
        await self.app.patch_slot("coyote", props={"connectState": "connected"}, slotState={"hasDevice": True})
        await self.until(lambda: self.route.connected)
        since = time.monotonic()
        await self.drive(.15, game=True)
        self.assertFalse(self.b.auto_output_enabled)
        self.assert_no_nonzero(since=since)
        self.b.toggleOutput()
        await self.drive(.18, game=True)
        self.assertTrue(self.app.pulses(since=since))
        self.b.emergencyStopAll()
        await self.drive(.18, game=True)
        since = time.monotonic()
        self.hub.clear_global_emergency_stop()
        await self.drive(.18, game=True)
        self.assertFalse(self.b.auto_output_enabled or self.b.ovc_enabled)
        self.assert_no_nonzero(since=since)
        self.assert_no_nonzero(since=since, slot="ovc")
        self.assertFalse(self.app.errors)

    async def test_09_backend_presets_custom_ab_sources_ramp_action_end_and_scene_exit(self):
        await self.ready()
        self.b.wave_map_value["high"] = "custom"
        self.b.custom_points_value = [0, 100, 0, 70] * 4
        self.b.custom_frequency_value = 77
        self.b.action_wave_map_value["SexStandBack"] = "official_tide"
        await self.arm_backend()
        self.feed(ecstasy=.1)
        await self.drive(.25, game=True)
        low = self.b.current_output_b
        self.feed(ecstasy=.9)
        await self.drive(.35, game=True)
        high = self.b.current_output_b
        self.assertGreater(high, low)
        self.assertEqual((self.b.current_wave_a.key, self.b.current_wave_b.key), ("custom", "official_tide"))
        self.assertTrue(any(r["data"]["v"][0].startswith("4D4D4D4D") for r in self.app.pulses(channel="A")))
        for sources in ({"A": "heart", "B": "heart"}, {"A": "action", "B": "action"}, {"A": "action", "B": "heart"}):
            self.b.pulse_channel_sources_value = sources
            self.b.wave_selector.reset()
            self.feed()
            await self.drive(.12, game=True)
            if sources["A"] == sources["B"]:
                self.assertEqual(self.b.current_frame.pattern_a, self.b.current_frame.pattern_b)
                self.assertEqual(self.b.current_wave_a.key, self.b.current_wave_b.key)
            else:
                self.assertEqual(self.b.current_wave_a.key, "official_tide")
                self.assertEqual(self.b.current_wave_b.key, "custom")
        self.b.pulse_channel_sources_value = {"A": "heart", "B": "action"}
        self.feed(action="None", playingAction=False)
        await self.drive(.18, game=True)
        self.assertGreater(self.b.current_output_a, 0)
        self.assertEqual(self.b.current_output_b, 0)
        # Manaka has no SiNiSistar2 CG playlist. Ending an action stops its
        # action channel while heart-rate output follows Manaka's own policy.
        self.feed(stage="None")
        await self.drive(.18, game=True)
        since = time.monotonic()
        await self.drive(.15, game=True)
        self.assertEqual((self.b.current_output_a, self.b.current_output_b, self.b.ovc_output), (0, 0, (0, 0)))
        self.assert_no_nonzero(since=since)
        self.assert_no_nonzero(since=since, slot="ovc")
        self.assertFalse(self.app.errors)

    async def test_10_ovc_independent_random_fixed_and_coyote3_fault_regression(self):
        await self.ready()
        await self.arm_backend()
        self.b.ovc_profile["channels"]["A"].update(mode="random", random_seconds=1, random_waves=["ovc_pulse", "ovc_ramp"])
        self.b.ovc_profile["channels"]["B"].update(mode="fixed", wave="ovc_breathe", strength=50)
        await self.drive(.22, game=True)
        self.assertEqual((self.b.ovc_frame["A"]["behavior"], self.b.ovc_frame["B"]["behavior"]), ("random", "fixed"))
        self.assertEqual(self.b.ovc_output, (40, 50))
        self.assertTrue(self.app.pulses("ovc", "A") and self.app.pulses("ovc", "B"))
        self.b.toggleOutput()
        self.b.selectV4Device("coyote", "", "")
        await self.until(lambda: not self.route.selected_slot_id)
        self.app.devices[0] = mock_device("COYOTE_030")
        await self.app.snapshot()
        await self.until(lambda: self.route.device_type == "COYOTE_030" and self.route.connected and self.b.device_connected_value)
        self.feed()
        self.b.toggleOutput()
        await self.until(lambda: self.b.auto_output_enabled and self.route._auto_enabled, game=True)
        await self.drive(.22, game=True)
        await self.app.patch_slot("coyote", props={"channelAStatus": 3})
        await self.drive(.13, game=True)
        since = time.monotonic()
        await self.drive(.2, game=True)
        self.assertFalse(self.app.pulses(channel="A", since=since))
        self.assertTrue(self.app.pulses(channel="B", since=since))
        self.assertTrue(self.app.pulses("ovc", "A", since=since))
        self.assertTrue(self.app.pulses("ovc", "B", since=since))
        self.assertFalse(self.app.errors)

    async def test_11_producer_expiry_drops_authority_and_shutdown_confirms_zero(self):
        await self.ready()
        await self.arm_wire()
        await self.drive(.75)
        self.assertFalse(self.route._auto_enabled)
        self.assertEqual(self.route._desired_updated_at, 0)
        since = time.monotonic()
        self.wire_plan()
        await self.drive(.15, wire=True)
        self.assert_no_nonzero(since=since)
        await self.arm_wire()
        await self.drive(.15, wire=True)
        since = time.monotonic()
        await asyncio.to_thread(self.hub.stop)
        self.assertFalse(self.hub.server_ready or self.route.connected)
        for channel in ("A", "B"):
            zeros = self.app.tasks(task_type=7, channel=channel, since=since)
            self.assertGreaterEqual(len(zeros), 2)
            replies = {r["reqId"]: r for r in self.app.responses}
            self.assertEqual(replies[zeros[-1]["reqId"]]["result"]["reason"], "completed")
        self.assertFalse(self.app.errors)


def run_validation(report_path) -> int:
    """Called by the source wrapper and the same frozen EXE transport modules."""
    EVIDENCE.clear()
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Coyote2ScenarioTests)
    started = time.monotonic()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    report = {
        "passed": result.wasSuccessful(), "tests_run": result.testsRun,
        "seconds": round(time.monotonic() - started, 3),
        "packaged_executable": bool(getattr(sys, "frozen", False)),
        "executable": sys.executable, "physical_hardware_connected": False,
        "verification_boundary": "Loopback APP only; Coyote 2.0 BLE/output/physical sensation NOT tested",
        "game_policy": "Manaka existing presets, custom waves, per-channel loop queues, action ramp and source routing preserved",
        "cg_policy": "SiNiSistar2 CG playlists are not a Manaka feature; action-end and nonplayable-scene stopping verified instead",
        "listen_host": "127.0.0.1", "test_log": stream.getvalue(),
        "failures": [str(case) + "\n" + trace for case, trace in result.failures + result.errors],
        "cases": EVIDENCE,
    }
    output = Path(report_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if sys.stdout is not None:
        print(json.dumps({k: report[k] for k in ("passed", "tests_run", "seconds", "packaged_executable", "physical_hardware_connected")}), flush=True)
        if not result.wasSuccessful():
            print(stream.getvalue().encode(getattr(sys.stdout, "encoding", None) or "utf-8", errors="backslashreplace").decode(getattr(sys.stdout, "encoding", None) or "utf-8"), flush=True)
    return 0 if result.wasSuccessful() else 1
