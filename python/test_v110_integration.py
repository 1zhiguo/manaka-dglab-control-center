"""Merged A/B engine -> V4 wire regressions, using only a loopback fake APP."""
import asyncio
from dataclasses import replace
import time
import unittest

from manaka_channel_engine import ChannelSettings, MappingSettings, migrate_settings
from manaka_runtime import DisplayMailbox, RealtimeProcessor, RuntimeConfig
from manaka_wave_rules import ChannelRules, WavePolicy
from manaka_waveforms import DEFAULT_WAVE_MAP, PRESETS
from test_realtime_runtime import FakeBridge, packet
import test_v4_bridge as wire


class RuntimeMergeTests(unittest.TestCase):
    def test_upstream_source_settings_migrate_and_route_in_background(self):
        mapping = migrate_settings({"pulse_channel_sources":{"A":"action","B":"heart"}})
        self.assertEqual(mapping.mode, "legacy_v1")
        config = RuntimeConfig(mapping=mapping, pulse_sources=(("A","action"),("B","heart")),
                               wave_map=tuple(DEFAULT_WAVE_MAP.items()))
        runtime = RealtimeProcessor(config, FakeBridge(), DisplayMailbox())
        snap = runtime.process(packet(1, action="None", playingAction=False))
        self.assertIsNone(snap.wave_a)
        self.assertGreater(snap.output_b, 0)
        self.assertEqual(snap.wave_b.key, DEFAULT_WAVE_MAP["high"])

    def test_switching_transport_retires_old_output_and_snapshot(self):
        old, new = FakeBridge(), FakeBridge()
        runtime = RealtimeProcessor(RuntimeConfig(), old, DisplayMailbox())
        runtime.process(packet(1))
        runtime.set_bridge(new)
        self.assertIsNone(runtime.latest)
        self.assertGreater(old.zeros, 0)
        runtime.process(packet(2))
        self.assertEqual(len(old.sent), 1)
        self.assertEqual(len(new.sent), 1)


class MergedV4WireTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = wire.V4WireTests.asyncSetUp
    asyncTearDown = wire.V4WireTests.asyncTearDown
    until = wire.V4WireTests.until
    read_phone = wire.V4WireTests.read_phone
    send = wire.V4WireTests.send
    select = wire.V4WireTests.select
    nonzero = wire.V4WireTests.nonzero

    async def coyote(self):
        raw = wire.device("COYOTE_030", "ovc", channelAStatus=0, channelBStatus=0)
        raw["slotState"]["channelA"]["intensityMax"] = 135
        raw["slotState"]["channelB"]["intensityMax"] = 185
        await self.send({"t":"ev", "ev":"slots.patch", "slots":[raw]})
        await self.until(lambda:self.bridge.devices_snapshot()[0]["type"] == "COYOTE_030")
        await self.select()

    async def test_background_engine_preserves_200_range_and_independent_device_caps(self):
        await self.coyote()
        a = ChannelSettings(maximum=200, hard_cap=160, attack=200)
        b = replace(a, hard_cap=190)
        runtime = RealtimeProcessor(RuntimeConfig(mapping=MappingSettings(A=a,B=b)), self.bridge, DisplayMailbox())
        for sequence in range(1,17):
            runtime.process(packet(sequence, monotonicMs=sequence*500))
            await asyncio.sleep(.012)
            self.bridge.set_auto_enabled(True)
            await asyncio.sleep(.06)
        self.assertEqual(runtime.rejected, 0)
        values = {c:[r["data"]["v"] for r in self.nonzero() if r["data"]["c"]==c] for c in (0,1)}
        self.assertEqual((max(values[0]), max(values[1])), (135,185))
        self.assertLessEqual(max(values[0]),160)
        # The loopback APP sees zero after a game pause, without a GUI tick.
        runtime.process(packet(17, monotonicMs=8500, paused=True))
        await self.until(lambda:not self.bridge.auto_enabled)
        self.assertEqual(self.bridge.channel_output("A"),0)

    async def test_one_shot_is_not_repeated_by_continuing_telemetry(self):
        await self.coyote()
        wave = PRESETS["heartbeat"].v3_frames()[:2]
        def update():
            self.bridge.update_auto_outputs(20,wave,wave_key_a="once|1",strength_b=0,frames_b=(),
                wave_key_b="idle",hard_cap=30,cap_a=25,cap_b=10,loop_a=False)
        update(); await asyncio.sleep(.01)
        self.bridge.set_auto_enabled(True)
        await self.until(lambda:self.bridge.auto_enabled)
        for _ in range(12):
            update(); await asyncio.sleep(.05)
        pulses = [r for r in self.records if r["m"]=="device.op" and r["data"]["t"]==0 and r["data"]["c"]==0]
        self.assertEqual(len(pulses),2)
        self.assertEqual(self.bridge.playback_state["A"],("once","completed"))
        self.assertEqual(self.bridge.channel_output("A"),0)

    async def test_cycle_switch_finishes_current_cycle_and_stale_updates_cannot_renew_lease(self):
        await self.coyote()
        old = tuple(f"0A0A0A0A{value:02X}{value:02X}{value:02X}{value:02X}" for value in (10,20,30))
        new = ("0A0A0A0A40404040",)
        def update(frames,key,**extra):
            self.bridge.update_auto_outputs(20,frames,wave_key_a=key,strength_b=0,frames_b=(),
                wave_key_b="idle",hard_cap=30,transition_a="cycle",**extra)
        update(old,"old"); await asyncio.sleep(.01); self.bridge.set_auto_enabled(True)
        def pulses():
            return [r["data"]["v"][0] for r in self.records if r["m"]=="device.op" and r["data"]["t"]==0 and r["data"]["c"]==0]
        await self.until(lambda:len(pulses())>=1)
        for _ in range(8):
            update(new,"new"); await asyncio.sleep(.05)
        self.assertEqual(pulses()[:4],list(old+new))
        receipt = self.bridge._desired_updated_at
        update(new,"new",received_at=time.monotonic()-1)
        await asyncio.sleep(.02)
        self.assertEqual(self.bridge._desired_updated_at,receipt)
        await self.until(lambda:not self.bridge.auto_enabled)

    async def test_long_library_stream_and_queued_write_cannot_survive_emergency_stop(self):
        await self.coyote()
        frames = PRESETS["heartbeat"].v3_frames()*120
        self.bridge.update_auto_outputs(20,frames,wave_key_a="library:long",strength_b=0,frames_b=(),wave_key_b="idle",hard_cap=30)
        await asyncio.sleep(.01)
        self.assertEqual(self.bridge._desired_frames["A"],frames)
        self.bridge.emergency_stop()
        self.bridge.update_auto_outputs(20,frames,wave_key_a="old",strength_b=0,frames_b=(),wave_key_b="idle",hard_cap=30)
        await asyncio.sleep(.05)
        self.assertEqual(self.bridge._desired_strength["A"],0)


if __name__ == "__main__":
    unittest.main()
