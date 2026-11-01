from dataclasses import replace
import math
import random
import unittest

from manaka_channel_engine import Binding, ChannelEngine, ChannelPeakLimiter, ChannelSettings, MappingSettings, migrate_settings


def packet(**changes):
    result = dict(stage="Residence", monotonicMs=10000, heartRate=160, action="Test", playingAction=True, ecstasy=1, orgasm=False)
    result.update(changes)
    return result


class IndependentChannelTests(unittest.TestCase):
    def test_output_boundaries_hold_across_varied_channel_settings(self):
        rng = random.Random(42)
        for _ in range(100):
            cap, cap_a, cap_b = [rng.randrange(101) for _ in range(3)]
            a = ChannelSettings(maximum=rng.randrange(101),hard_cap=cap_a,attack=100,
                                bindings=(Binding(source="ecstasy"),))
            b = replace(a,maximum=rng.randrange(101),hard_cap=cap_b)
            engine = ChannelEngine(MappingSettings(global_cap=cap,A=a,B=b))
            frame = engine.evaluate(packet(ecstasy=rng.random()),.5)
            self.assertTrue(0 <= frame.strength_a <= min(cap,cap_a))
            self.assertTrue(0 <= frame.strength_b <= min(cap,cap_b))
            paused = engine.evaluate(packet(paused=True))
            self.assertEqual((paused.strength_a,paused.strength_b),(0,0))
    def test_continuous_thresholds_and_curves_are_configurable(self):
        for curve, expected in (("linear",5), ("ease_in",1.25), ("ease_out",10)):
            binding = Binding(source="ecstasy", input_start=20, input_full=100, curve=curve)
            channel = ChannelSettings(maximum=20,attack=100,bindings=(binding,))
            engine = ChannelEngine(MappingSettings(A=channel))
            self.assertEqual(engine.evaluate(packet(ecstasy=.1),.5).strength_a,0)
            self.assertEqual(engine.evaluate(packet(ecstasy=.4),.5).strength_a,expected)
    def test_sources_can_be_swapped_or_shared_and_combined(self):
        heart = Binding(source="heart")
        action = Binding(source="action")
        base = ChannelSettings(maximum=20, attack=100, bindings=(action,))
        engine = ChannelEngine(MappingSettings(A=base, B=replace(base, bindings=(heart,))))
        frame = engine.evaluate(packet(heartRate=160, ecstasy=.3), .5)
        self.assertEqual((frame.strength_a, frame.strength_b), (6, 20))
        shared = ChannelEngine(MappingSettings(A=base, B=base)).evaluate(packet(ecstasy=.3), .5)
        self.assertEqual((shared.strength_a, shared.strength_b), (6, 6))
        for combine, expected in (("max", 10), ("weighted", round(16 / 1.5, 3))):
            channel = replace(base, combine=combine, bindings=(replace(heart, weight=.5), action))
            frame = ChannelEngine(MappingSettings(A=channel)).evaluate(packet(ecstasy=.3), .5)
            self.assertEqual(frame.strength_a, expected)

    def test_discrete_percentages_are_relative_to_maximum_not_minimum_or_cap(self):
        a = ChannelSettings(minimum=5, maximum=20, hard_cap=90, attack=100, bindings=(Binding(source="vibrator"),))
        frame = ChannelEngine(MappingSettings(A=a, global_cap=90)).evaluate(packet(
            version=2, hasVibratorData=True, vibratorEffectiveMode="Low"), .5)
        self.assertEqual(frame.strength_a, 6)

    def test_caps_do_not_scale_ordinary_targets_and_channels_are_independent(self):
        a = ChannelSettings(maximum=20, hard_cap=25, attack=100, bindings=(Binding(source="action"),))
        b = replace(a, maximum=8)
        engine = ChannelEngine(MappingSettings(A=a, B=b, global_cap=80))
        first = engine.evaluate(packet(ecstasy=.3), .5)
        self.assertEqual((first.strength_a, first.strength_b), (6, 2.4))
        other = ChannelEngine(replace(engine.settings, A=replace(a, hard_cap=90)))
        self.assertEqual(other.evaluate(packet(ecstasy=.3), .5), first)

    def test_climax_uses_ordinary_maximum_and_only_enabled_channels(self):
        settings = MappingSettings(A=ChannelSettings(maximum=20), B=ChannelSettings(climax=replace(ChannelSettings().climax, enabled=False)))
        engine = ChannelEngine(settings)
        engine.evaluate(packet())
        frame = engine.evaluate(packet(orgasm=True, monotonicMs=10100))
        self.assertEqual(frame.strength_a, 18)
        self.assertNotEqual(frame.pattern_b, "peak")
        self.assertEqual(frame.events, ("A:climax",))
        repeated = engine.evaluate(packet(orgasm=True, monotonicMs=10200))
        self.assertEqual(repeated.events, ())

    def test_pause_disabled_and_missing_data_cut_immediately(self):
        engine = ChannelEngine()
        engine.evaluate(packet(), .5)
        for value in (dict(paused=True), dict(systemMenuOpen=True), dict(panic=True), dict(armed=False), dict(timeScale=0)):
            frame = engine.evaluate(packet(**value))
            self.assertTrue(frame.safe_cut)
            self.assertEqual((frame.strength_a, frame.strength_b), (0, 0))
        engine = ChannelEngine(MappingSettings(A=replace(ChannelSettings(), enabled=False)))
        self.assertEqual(engine.evaluate(packet(), .5).strength_a, 0)
        engine.evaluate(packet(), .5)
        self.assertEqual(engine.evaluate({"stage":"Residence"}).strength_b, 0)

    def test_peak_history_does_not_couple_channels_and_cap_is_final(self):
        limiter = ChannelPeakLimiter()
        limiter.apply("A", 60, peak=False, now=1, cap=80)
        limiter.apply("B", 2, peak=False, now=1, cap=20)
        self.assertEqual(limiter.apply("A", 90, peak=True, now=2, cap=70), 70)
        self.assertEqual(limiter.apply("B", 90, peak=True, now=2, cap=20), 17)
        self.assertEqual(limiter.apply("B", 90, peak=True, now=2.1, cap=10), 10)

    def test_legacy_migration_requires_explicit_switch_and_roundtrips(self):
        migrated = migrate_settings(dict(hard_cap=40, min_strength=3, output_max=15))
        self.assertEqual(migrated.mode, "legacy_v1")
        self.assertEqual(migrated.A.maximum, 15)
        self.assertEqual(MappingSettings.parse(migrated.to_dict()), migrated)
        self.assertEqual(migrate_settings({"channel_mapping":migrated.to_dict()}), migrated)

    def test_invalid_configuration_is_rejected(self):
        for key, value in (("attack", math.nan), ("minimum", 101), ("enabled", "false"), ("combine", "sum")):
            raw = MappingSettings().to_dict()
            raw["A"][key] = value
            with self.assertRaises(ValueError):
                MappingSettings.parse(raw)
