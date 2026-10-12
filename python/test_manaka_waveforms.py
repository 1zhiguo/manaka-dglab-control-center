import unittest

from manaka_waveforms import (
    DEFAULT_WAVE_MAP,
    PRESETS,
    WaveformPreset,
    WaveformSelector,
    action_label,
    action_style,
    recommended_wave_for_action,
    resolve_waveform,
    sanitize_wave_map,
)


class WaveformTests(unittest.TestCase):
    def test_all_presets_encode_valid_v3_frames(self):
        for preset in PRESETS.values():
            frames = preset.v3_frames()
            self.assertEqual(len(frames), len(preset.amplitudes))
            self.assertTrue(all(len(frame) == 16 for frame in frames))
            self.assertTrue(all(int(frame, 16) >= 0 for frame in frames))

    def test_smart_mode_maps_heart_rate_zones(self):
        self.assertEqual(resolve_waveform("heartbeat-soft", "smart", "steps", DEFAULT_WAVE_MAP).key, "official_breath")
        self.assertEqual(resolve_waveform("heartbeat", "smart", "steps", DEFAULT_WAVE_MAP).key, "official_heartbeat")
        self.assertEqual(resolve_waveform("heartbeat-fast", "smart", "steps", DEFAULT_WAVE_MAP).key, "official_pulsating")

    def test_fixed_mode_uses_one_preset_for_active_patterns(self):
        self.assertEqual(resolve_waveform("heartbeat-soft", "fixed", "stream", DEFAULT_WAVE_MAP).key, "stream")
        self.assertEqual(resolve_waveform("action-ramp", "fixed", "stream", DEFAULT_WAVE_MAP).key, "stream")

    def test_idle_never_resolves_to_a_waveform(self):
        self.assertIsNone(resolve_waveform("idle", "fixed", "burst", DEFAULT_WAVE_MAP))

    def test_custom_waveform_can_be_assigned(self):
        custom = WaveformPreset("custom", "Mine", "", "", "#fff", (0, 50, 100), (90,))
        mapping = sanitize_wave_map({"low": "custom"})
        self.assertEqual(resolve_waveform("heartbeat-soft", "smart", "heartbeat", mapping, custom).key, "custom")

    def test_invalid_mapping_falls_back_to_defaults(self):
        mapping = sanitize_wave_map({"low": "missing", "mid": "steps"})
        self.assertEqual(mapping["low"], DEFAULT_WAVE_MAP["low"])
        self.assertEqual(mapping["mid"], "steps")

    def test_channel_a_zone_change_is_debounced(self):
        selector = WaveformSelector(hold_seconds=0.8)
        first = selector.select("A", "heartbeat-soft", "smart", "heartbeat", DEFAULT_WAVE_MAP, now=1.0)
        pending = selector.select("A", "heartbeat", "smart", "heartbeat", DEFAULT_WAVE_MAP, now=1.2)
        committed = selector.select("A", "heartbeat", "smart", "heartbeat", DEFAULT_WAVE_MAP, now=2.1)
        self.assertEqual(first.key, "official_breath")
        self.assertEqual(pending.key, "official_breath")
        self.assertEqual(committed.key, "official_heartbeat")

    def test_idle_cut_is_immediate(self):
        selector = WaveformSelector(hold_seconds=0.8)
        selector.select("A", "heartbeat", "smart", "heartbeat", DEFAULT_WAVE_MAP, now=1.0)
        self.assertIsNone(selector.select("A", "idle", "smart", "heartbeat", DEFAULT_WAVE_MAP, now=1.1))

    def test_action_types_receive_safe_recommended_waveforms(self):
        self.assertEqual(action_style("PickUpItem"), "off")
        self.assertEqual(recommended_wave_for_action("PickUpItem"), "off")
        self.assertEqual(action_style("Dogeza"), "static")
        self.assertEqual(recommended_wave_for_action("Dogeza"), "official_breath")
        self.assertEqual(action_style("OnaniNormal"), "rhythmic")
        self.assertEqual(recommended_wave_for_action("OnaniNormal"), "official_heartbeat")
        self.assertEqual(recommended_wave_for_action("UseDildoFloorPussy1"), "official_pulsating")

    def test_action_labels_are_localized_without_changing_keys(self):
        self.assertEqual(action_label("Pinpon", "zh"), "按门铃")
        self.assertEqual(action_label("Dogeza", "zh"), "土下座")
        self.assertEqual(action_label("UseDildoFloorPussy3", "zh"), "地面假阳具 · 阴道动作 3")
        self.assertEqual(action_label("UseDildoWallWaitAnal", "zh"), "墙面假阳具 · 肛门待机")
        self.assertEqual(action_label("UseDildoWallFellaEcstasyA", "zh"), "墙面假阳具 · 口交高潮")
        self.assertEqual(action_label("FutureAction42", "en"), "Future Action 42")


if __name__ == "__main__":
    unittest.main()
