"""Normalized intensity mixing; tests use only pure engines and a fake bridge."""
from dataclasses import replace
import unittest

from manaka_channel_engine import Binding, ChannelEngine, ChannelSettings, MappingSettings
from manaka_runtime import DisplayMailbox, RealtimeProcessor, RuntimeConfig
from test_realtime_runtime import FakeBridge, packet


class WeightedAverageTests(unittest.TestCase):
    def settings(self, **changes):
        return ChannelSettings(maximum=100, hard_cap=100, attack=100, release=100,
            combine="weighted", bindings=(Binding(source="heart"), Binding(source="ecstasy")), **changes)

    def settle(self, channel, **values):
        engine = ChannelEngine(MappingSettings(A=channel))
        for n in range(10):
            frame = engine.evaluate(packet(n + 1, **values), .5)
        return frame.strength_a

    def test_two_middle_sources_average_without_saturating(self):
        self.assertEqual(self.settle(self.settings(), heartRate=125, ecstasy=.6), 55)

    def test_scaling_all_weights_preserves_relative_mix(self):
        for scale in (.01, 1, 10):
            channel = replace(self.settings(), bindings=(
                Binding(source="heart", weight=.2 * scale), Binding(source="ecstasy", weight=.8 * scale)))
            with self.subTest(scale=scale):
                self.assertEqual(self.settle(channel, heartRate=160, ecstasy=.5), 60)

    def test_inactive_or_missing_source_keeps_denominator_and_never_boosts_peer(self):
        for missing in (False, True):
            with self.subTest(missing=missing):
                engine = ChannelEngine(MappingSettings(A=self.settings()))
                # Full-scale heart and low ecstasy => 60. Removing the low
                # source must produce 50, not amplify the heart source to 100.
                for n in range(10):
                    before = engine.evaluate(packet(n + 1, heartRate=160, ecstasy=.2), .5)
                after_packet = packet(11, heartRate=160, ecstasy=0)
                if missing:
                    del after_packet["ecstasy"]
                after = engine.evaluate(after_packet, .5)
                self.assertEqual((before.strength_a, after.strength_a), (60, 50))

    def test_zero_weights_and_no_active_sources_produce_zero(self):
        channel = self.settings()
        zero = replace(channel, bindings=tuple(replace(b, weight=0) for b in channel.bindings))
        self.assertEqual(self.settle(zero, heartRate=160, ecstasy=1), 0)
        self.assertEqual(self.settle(channel, heartRate=0, ecstasy=0), 0)
        one = replace(channel, bindings=(Binding(source="heart", weight=0), Binding(source="ecstasy")))
        self.assertEqual(self.settle(one, heartRate=160, ecstasy=.4), 40)

    def test_minimum_is_not_summed_and_inactive_source_has_no_minimum(self):
        channel = self.settings(minimum=20)
        self.assertEqual(self.settle(channel, heartRate=104, ecstasy=.2), 36)
        self.assertEqual(self.settle(channel, heartRate=104, ecstasy=0), 18)

    def test_saved_key_weights_ranges_and_caps_roundtrip_unchanged(self):
        channel = replace(self.settings(), minimum=40, maximum=200, hard_cap=160, bindings=(
            Binding(source="vibrator", weight=.8), Binding(source="heart", weight=.2),
            Binding(source="ecstasy", weight=.5), Binding(source="npc_alert", weight=.3)))
        raw = MappingSettings(A=channel).to_dict()
        parsed = MappingSettings.parse(raw)
        self.assertEqual(parsed.to_dict(), raw)
        output = self.settle(parsed.A, heartRate=125, ecstasy=.5, maxNpcAlert=.5,
                             version=2, hasVibratorData=True, vibratorEffectiveMode="low")
        self.assertEqual(output, 93.333)
        self.assertEqual(parsed.to_dict(), raw)

    def test_hard_cap_and_maximum_algorithm_keep_their_previous_behavior(self):
        channel = replace(self.settings(), hard_cap=20)
        self.assertEqual(self.settle(channel, heartRate=160, ecstasy=1), 20)
        maximum = replace(channel, combine="max", hard_cap=100, bindings=(
            Binding(source="heart", weight=.5), Binding(source="ecstasy")))
        self.assertEqual(self.settle(maximum, heartRate=160, ecstasy=.6), 60)

    def test_full_runtime_stays_below_cap_then_releases_without_peer_amplification(self):
        channel = replace(self.settings(), attack=12, release=24)
        mapping = MappingSettings(A=channel, B=replace(channel, hard_cap=20))
        bridge, clock = FakeBridge(), [100.]
        runtime = RealtimeProcessor(RuntimeConfig(mapping=mapping), bridge, DisplayMailbox(), clock=lambda:clock[0])
        values = []
        for n in range(1, 601):
            clock[0] = 100 + n * .1
            snapshot = runtime.process(packet(n, heartRate=125, ecstasy=.6))
            self.assertIsNotNone(snapshot)
            values.append(snapshot.output_a)
        self.assertEqual(set(values[300:]), {55})
        self.assertEqual(snapshot.output_b, 20)
        self.assertLess(max(values), 100)
        previous = values[-1]
        for n in range(601, 651):
            clock[0] = 100 + n * .1
            snapshot = runtime.process(packet(n, heartRate=125, ecstasy=0))
            self.assertLessEqual(snapshot.output_a, previous)
            previous = snapshot.output_a
        self.assertEqual(snapshot.output_a, 25)
        # Device limits and pause zeroing still apply after normalization.
        bridge.channel_limit = lambda channel: 7
        clock[0] += .1
        self.assertEqual(runtime.process(packet(651, heartRate=125, ecstasy=0)).output_a, 7)
        clock[0] += .1
        stopped = runtime.process(packet(652, paused=True))
        self.assertEqual((stopped.output_a, stopped.output_b), (0, 0))


if __name__ == "__main__":
    unittest.main()
