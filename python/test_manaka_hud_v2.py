import unittest
from manaka_devices.hud_settings import DEFAULTS, sanitize_settings, build_packet
from test_manaka_ovc import Harness


class HudV2Tests(unittest.TestCase):
    def packet(self, settings=None):
        return build_packet(1, settings or DEFAULTS, visible=True, connected=(True, True), active=(True, False),
                            strengths=(120, -1, 250, float("nan")), caps=(30, 30, 200, 200), pulses=(1.8, -1, .5, 0))

    def test_v2_shape_is_bounded_and_finite(self):
        data = self.packet()
        parts = data.decode("ascii").split("|")
        self.assertEqual(len(parts), 24)
        self.assertEqual(parts[0], "MANAKA_HUD_V2")
        self.assertEqual(parts[-1], "END")
        self.assertEqual(parts[11:15], ["100.00", "0.00", "200.00", "0.00"])
        self.assertLess(len(data), 512)

    def test_content_mask_and_custom_placement(self):
        settings = {**DEFAULTS, "show_pulse": False, "show_a": False, "anchor": "custom", "x": 99, "y": 5}
        parts = self.packet(settings).decode().split("|")
        self.assertEqual(parts[6:9], ["7", "99", "5"])
        self.assertFalse(int(parts[3]) & 1)
        self.assertFalse(int(parts[3]) & 4)

    def test_invalid_inputs_fall_back_to_bounded_settings(self):
        settings = sanitize_settings({"scale": 999, "opacity": -10, "anchor": "bad", "x": float("inf"), "show_pulse": False, "show_ovc": False})
        self.assertEqual((settings["scale"], settings["opacity"], settings["anchor"]), (180, 0, "game_safe"))
        self.assertTrue(settings["show_pulse"])

    def test_hud_save_never_changes_device_output(self):
        b = Harness()
        b.ovc_enabled = True
        self.assertTrue(b.saveHudSettings({**DEFAULTS, "scale": 80}))
        self.assertEqual(set(b.persist.call_args.args[0]), {"hud_settings"})
        self.assertTrue(b.auto_output_enabled)
        self.assertTrue(b.ovc_enabled)
        b.bridge.emergency_stop.assert_not_called()
        b.v4_hub.channel.return_value.emergency_stop.assert_not_called()

    def test_failed_save_and_empty_content_are_rejected(self):
        b = Harness()
        self.assertFalse(b.saveHudSettings({**DEFAULTS, "show_a": False, "show_b": False}))
        b.persist.side_effect = OSError("full")
        self.assertFalse(b.saveHudSettings({**DEFAULTS, "scale": 80}))
        self.assertEqual(b.hud_settings, DEFAULTS)

    def test_old_plugin_is_detected_without_blocking_telemetry(self):
        b = Harness()
        self.assertIn("update needed", b.hudPluginHint)
        b.last_packet["hudProtocol"] = 2
        self.assertIn("V2", b.hudPluginHint)


if __name__ == "__main__":
    unittest.main()
