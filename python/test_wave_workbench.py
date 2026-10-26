import json
import unittest
from dataclasses import replace

from manaka_channel_engine import Binding, ChannelSettings, MappingSettings
from manaka_wave_library import parse_import, frames_valid, encode_period, decode_period, preview_samples
from manaka_wave_player import ChannelPlayer
from manaka_wave_rules import WaveRule, ChannelRules, WavePolicy, WaveRouter, migrate_policy
from manaka_runtime import RuntimeConfig, RealtimeProcessor, DisplayMailbox
from test_realtime_runtime import FakeBridge, packet


class LibraryTests(unittest.TestCase):
    def test_raw_subframes_roundtrip_without_16_point_loss(self):
        frames = ["0A141E2800326464"]*31
        raw = json.dumps(dict(name="test", frame_ms=100, frames=frames))
        result = parse_import(raw)[0]
        self.assertEqual(result["frames"],tuple(frames))
        preview = preview_samples(result["frames"])
        self.assertEqual(preview["durationMs"],3100)
        self.assertEqual(preview["amplitudes"][:4],[0,50,100,100])
        self.assertEqual(preview["periodsMs"][:4],[10,20,30,40])

    def test_reference_json_text_and_old_local_formats(self):
        self.assertEqual(len(parse_import('{"waveforms":[{"name":"a","frames":[[10,100]]},{"name":"b","frames":[[20,0]]}]}')),2)
        self.assertEqual(parse_import("# test\n10, 100\n1414141400000000")[0]["frames"],("0A0A0A0A64646464","1414141400000000"))
        self.assertEqual(len(parse_import(json.dumps(dict(points=[25]*16,frequency=92)))[0]["frames"]),16)

    def test_dungeonlab_period_encoding_duration_and_rest(self):
        # Index 70 is 200 ms (5 Hz), encoded as 120, not a literal Hz value.
        from manaka_wave_library import PERIODS
        index = PERIODS.index(200)
        result = parse_import(f"Dungeonlab+pulse:100,1={index},{index},2,1,1/100-0,50-0")[0]
        self.assertEqual(len(result["frames"]),4)  # 100 ms rest + exactly 300 ms section
        self.assertEqual(result["frames"][1],"7878787864646464")
        self.assertEqual(decode_period(encode_period(200)),200)

    def test_invalid_file_is_rejected_without_partial_import(self):
        for raw in ("0A0A0A0A65646464", "090A0A0A00000000", '{"frames":[],"frame_ms":25}',
                    '{"waveforms":[{"frames":[[10,100]]},{"frames":[[250,100]]}]}'):
            with self.assertRaises(ValueError):
                parse_import(raw)


class PlayerTests(unittest.TestCase):
    def test_short_and_long_loops_are_continuous_with_bounded_queue(self):
        for count in (1,3,8,10,82):
            p = ChannelPlayer()
            frames = tuple(f"{10+i%100:02X}"*4+"01010101" for i in range(count))
            sent = []
            for tick in range(2400):
                now = tick*.025
                previous = p.queued_until
                plan = p.plan(now,"wave",frames)
                if plan.frames:
                    if sent:
                        self.assertLessEqual(now,previous+.026)
                    sent.extend(plan.frames)
                self.assertLessEqual(p.queued_until-now,.301)
            self.assertEqual(sent, [frames[i%count] for i in range(len(sent))])

    def test_once_plays_complete_long_asset_and_never_repeats(self):
        p = ChannelPlayer(); frames = ("0A0A0A0A01010101",)*37
        output = []; finished=False
        for tick in range(400):
            plan=p.plan(tick*.025,"event1",frames,False)
            output.extend(plan.frames); finished |= plan.finished
        self.assertEqual(len(output),37)
        self.assertTrue(finished)
        self.assertTrue(p.plan(11,"event2",frames,False).clear)
        self.assertTrue(p.plan(11.2,"event2",frames,False).frames)

    def test_switch_discards_old_queue_and_waits_without_blocking_other_channel(self):
        a,b=ChannelPlayer(),ChannelPlayer();frames=("0A0A0A0A01010101",)*10
        for p in (a,b):p.plan(0,"old",frames)
        self.assertTrue(a.plan(.15,"old",frames).frames)
        self.assertTrue(a.plan(.2,"new",frames).clear)
        self.assertFalse(a.plan(.25,"new",frames).frames)
        self.assertTrue(b.plan(.25,"old",frames).frames)
        self.assertTrue(a.plan(.36,"new",frames).frames)


class RulesTests(unittest.TestCase):
    def evaluate(self, router, now, **values):
        return router.evaluate(packet(**values),now,lambda key,wave:1.)

    def test_priority_debounce_hold_and_independent_channels(self):
        rule=WaveRule("move","action","official_tide",value="Walking",stable_ms=200,hold_ms=500)
        router=WaveRouter(WavePolicy(A=ChannelRules("official_breath",rules=(rule,))))
        self.assertEqual(self.evaluate(router,0)["A"].wave,"official_breath")
        self.assertEqual(self.evaluate(router,.1,action="Walking",playingAction=True)["A"].wave,"official_breath")
        self.assertEqual(self.evaluate(router,.4,action="Walking",playingAction=True)["A"].wave,"official_tide")
        self.assertEqual(self.evaluate(router,.5)["A"].wave,"official_tide")
        self.assertEqual(self.evaluate(router,1)["A"].wave,"official_breath")
        self.assertEqual(self.evaluate(router,1)["B"].reason,"default")

    def test_event_preemption_restores_current_state_not_stale_action(self):
        rules=(WaveRule("move","action","official_tide",value="Walking",stable_ms=0),
               WaveRule("event","climax","climax",priority=100,playback="once",duration_ms=1000))
        router=WaveRouter(WavePolicy(A=ChannelRules("official_breath",rules=rules)))
        self.evaluate(router,0,action="Walking",playingAction=True)
        selected=self.evaluate(router,.1,orgasm=True)["A"]
        self.assertEqual(selected.wave,"climax");self.assertFalse(selected.loop)
        self.assertEqual(self.evaluate(router,1.2,action="Standing")["A"].wave,"official_breath")

    def test_cycle_switch_crosses_boundary_even_with_sparse_updates(self):
        rule=WaveRule("move","action","official_tide",value="Walking",stable_ms=0,transition="cycle")
        router=WaveRouter(WavePolicy(A=ChannelRules("official_breath",rules=(rule,))))
        self.evaluate(router,0)
        self.assertEqual(self.evaluate(router,.2,action="Walking",playingAction=True)["A"].wave,"official_breath")
        self.assertEqual(self.evaluate(router,1.4,action="Walking",playingAction=True)["A"].wave,"official_tide")

    def test_single_policy_wins_even_when_strength_sources_are_weighted(self):
        mapping=MappingSettings(A=ChannelSettings(combine="weighted",bindings=(Binding(source="heart",wave="official_tide"),Binding(source="ecstasy",wave="official_ripple"))))
        policy=WavePolicy(A=ChannelRules("official_breath"))
        bridge=FakeBridge();processor=RealtimeProcessor(RuntimeConfig(mapping=mapping,wave_policy=policy),bridge,DisplayMailbox())
        snapshot=processor.process(packet())
        self.assertEqual(snapshot.wave_a.key,"official_breath")
        self.assertEqual(bridge.sent[-1][0][1],snapshot.wave_a.v3_frames())
        self.assertNotIn("mixed",snapshot.wave_a.key)

    def test_migration_preserves_explicit_wave_and_fixed_default(self):
        settings=MappingSettings(A=ChannelSettings(bindings=(Binding(source="heart",wave="official_tide"),)))
        policy=migrate_policy(dict(wave_mode="fixed",fixed_wave="official_breath"),settings)
        self.assertEqual(policy.A.default_wave,"official_breath")
        self.assertEqual(policy.A.rules[0].wave,"official_tide")
        self.assertEqual(WavePolicy.parse(policy.to_dict()),policy)

    def test_piston_numeric_mode_matches_named_rule(self):
        policy = WavePolicy(A=ChannelRules(rules=(WaveRule("medium", "piston", "official_tide", value="medium", stable_ms=0),)))
        selected = self.evaluate(WaveRouter(policy), 0, hasPistonData=True, pistonEffectiveMode=2)
        self.assertEqual(selected["A"].wave, "official_tide")

    def test_action_migration_groups_without_losing_overrides_or_exceeding_limits(self):
        settings = MappingSettings(A=ChannelSettings(bindings=tuple(Binding(source="action") for _ in range(6))))
        policy = migrate_policy(dict(action_wave_map={"MyAction":"official_tide"}), settings)
        self.assertLess(len(policy.A.rules), 128)
        self.assertEqual(WavePolicy.parse(policy.to_dict()), policy)
        selected = self.evaluate(WaveRouter(policy), 0, action="MyAction", playingAction=True)
        self.assertEqual(selected["A"].wave, "official_tide")

    def test_resume_rebaselines_event_already_active_while_paused(self):
        bridge = FakeBridge()
        clock = [10.]
        policy = WavePolicy(A=ChannelRules(rules=(WaveRule("event", "climax", "climax", playback="once"),)))
        processor = RealtimeProcessor(RuntimeConfig(wave_policy=policy), bridge, DisplayMailbox(), clock=lambda:clock[0])
        processor.process(packet(1))
        bridge.auto_enabled = False
        clock[0] += .1
        processor.process(packet(2, orgasm=True))
        bridge.auto_enabled = True
        clock[0] += .1
        resumed = processor.process(packet(3, orgasm=True))
        self.assertEqual(resumed.reason_a, "default")
        self.assertEqual(resumed.frame.events, ())

    def test_climax_has_fixed_priority_and_can_be_disabled(self):
        for enabled in (True, False):
            bridge = FakeBridge()
            clock = [10.]
            policy = WavePolicy(A=ChannelRules(rules=(WaveRule("ordinary", "always", priority=200),
                WaveRule("event", "climax", "climax", priority=100, playback="once", enabled=enabled))))
            mapping = MappingSettings()
            processor = RealtimeProcessor(RuntimeConfig(mapping=mapping, wave_policy=policy), bridge, DisplayMailbox(), clock=lambda:clock[0])
            processor.process(packet(1))
            clock[0] += .1
            selected = processor.process(packet(2, orgasm=True))
            self.assertEqual(selected.frame.pattern_a == "peak", enabled)
            self.assertEqual(selected.reason_a, "event · climax" if enabled else "ordinary · always")

    def test_climax_preempts_simultaneous_failure_and_uses_climax_strength(self):
        bridge = FakeBridge()
        clock = [10.]
        mapping = MappingSettings(A=replace(ChannelSettings(), climax=replace(ChannelSettings().climax,percent=20),
            failure=replace(ChannelSettings().failure, enabled=True, percent=50)))
        policy = WavePolicy(A=ChannelRules(rules=(WaveRule("climax", "climax", "climax", priority=150),
            WaveRule("failure", "failure", "official_tide", priority=200))))
        processor = RealtimeProcessor(RuntimeConfig(mapping=mapping,wave_policy=policy),bridge,DisplayMailbox(),clock=lambda:clock[0])
        processor.process(packet(1))
        clock[0] += .1
        selected = processor.process(packet(2, orgasm=True, gameOver=True))
        self.assertEqual(selected.reason_a, "climax · climax")
        self.assertEqual(selected.frame.strength_a, 4)


class CycleTransportTests(unittest.TestCase):
    def test_transition_finishes_actual_cycle_including_settle_time(self):
        player = ChannelPlayer()
        old = tuple(f"0A0A0A0A{i:02X}{i:02X}{i:02X}{i:02X}" for i in range(7))
        new = ("1414141464646464",)
        sent = []
        switched_at = None
        for step in range(50):
            now = step*.025
            changed = now >= .45
            plan = player.plan(now, "new" if changed else "old", new if changed else old, transition="cycle" if changed else "immediate")
            if changed and plan.clear:
                switched_at = now
                break
            sent.extend(plan.frames)
        self.assertEqual(sent, list(old))
        self.assertIsNotNone(switched_at)
        self.assertGreaterEqual(switched_at, .85-1e-9)
        self.assertLess(switched_at, .9)
