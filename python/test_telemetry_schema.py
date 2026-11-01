import unittest
from manaka_channel_engine import Binding, ChannelEngine, ChannelSettings, MappingSettings
from manaka_telemetry_schema import detections


class DetectionTests(unittest.TestCase):
    def test_legacy_configured_random_mode_is_not_actual_state(self):
        state = detections(dict(version=1, vibration="Random", piston=4))
        self.assertFalse(state["vibrator"].available)
        self.assertFalse(state["piston"].available)

    def test_random_uses_actual_mode_and_separate_percentages(self):
        packet = dict(version=2, stage="Residence", hasVibratorData=True,
            vibratorConfiguredMode="Random", vibratorEffectiveMode="High",
            hasPistonData=True, pistonRandom=True, pistonEffectiveMode=1)
        settings = MappingSettings(
            A=ChannelSettings(maximum=20, attack=100, bindings=(Binding(source="vibrator", strong=80),)),
            B=ChannelSettings(maximum=10, attack=100, bindings=(Binding(source="piston", weak=25),)))
        frame = ChannelEngine(settings).evaluate(packet, .5)
        self.assertEqual((frame.strength_a, frame.strength_b), (16, 2.5))
        packet["pistonEffectiveMode"] = 3
        self.assertEqual(ChannelEngine(settings).evaluate(packet, .5).strength_b, 7)

    def test_invalid_and_explicitly_missing_fields_are_unavailable(self):
        for packet in (dict(version=2, hasVibratorData=False, vibratorEffectiveMode="High"),
                       dict(version=2, hasVibratorData=True, vibratorEffectiveMode="Random"),
                       dict(version=2, hasPistonData=True, pistonEffectiveMode=4)):
            state = detections(packet)
            self.assertFalse(state["vibrator"].available)
            self.assertFalse(state["piston"].available)
        self.assertFalse(detections({"heartRate":float("nan")})["heart"].available)
        self.assertFalse(detections({"ecstasy":float("inf")})["ecstasy"].available)

    def test_off_and_unavailable_are_distinct_but_both_zero(self):
        off = detections(dict(version=2, hasPistonData=True, pistonEffectiveMode=0))["piston"]
        self.assertTrue(off.available)
        self.assertFalse(off.active)
        self.assertFalse(detections({})["piston"].available)
