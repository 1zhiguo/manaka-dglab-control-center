import random
import unittest
from copy import deepcopy
from unittest.mock import MagicMock

from manaka_devices.ovc import OvcPlanner, sanitize_profile, waveform_catalog, wave_frames
from test_manaka_ovc import Harness


class AdvancedOvcTests(unittest.TestCase):
    def profile(self):
        profile = sanitize_profile({"mode": "independent", "channel_b": True})
        profile["channels"]["B"]["enabled"] = True
        return profile

    def evaluate(self, profile, packet=None, planner=None, now=1, fresh=True, authorized=True):
        packet = {"stage": "Stage02", "vibration": "Low", "action": "Walking", **(packet or {})}
        return (planner or OvcPlanner()).evaluate(packet, profile, waveform_catalog(profile), now=now, fresh=fresh, authorized=authorized)

    def test_legacy_profile_migrates_without_losing_values(self):
        p = sanitize_profile({"low": 20, "high": 50, "random": 30, "hard_cap": 50, "channel_b": True})
        self.assertEqual((p["low"], p["high"], p["mode"]), (20, 50, "sync"))
        self.assertTrue(p["channels"]["B"]["enabled"])

    def test_mixed_sync_and_fixed_channels(self):
        p = self.profile()
        p["channels"]["B"].update(mode="fixed", wave="ovc_pulse", strength=30)
        frame = self.evaluate(p)
        self.assertEqual((frame["A"]["strength"], frame["B"]["strength"]), (10, 30))
        frame = self.evaluate(p, {"vibration": "Off"})
        self.assertEqual((frame["A"]["strength"], frame["B"]["strength"]), (0, 30))

    def test_action_override_and_unmapped_sync_fallback(self):
        p = self.profile()
        p["channels"]["A"].update(mode="action", actions={"Walking": {"mode": "wave", "wave": "ovc_ramp", "strength": 20}})
        frame = self.evaluate(p)
        self.assertEqual((frame["A"]["wave"], frame["A"]["strength"], frame["B"]["strength"]), ("ovc_ramp", 20, 10))
        self.assertEqual(self.evaluate(p, {"action": "NewModAction"})["A"]["strength"], 10)
        self.assertEqual(self.evaluate(p, {"action": "NewModAction", "vibration": "Off"})["A"]["strength"], 0)

    def test_action_can_explicitly_sync_or_turn_off(self):
        p = self.profile()
        p["channels"]["A"].update(mode="action", actions={"Walking": {"mode": "off"}})
        self.assertEqual(self.evaluate(p)["A"]["strength"], 0)
        p["channels"]["A"]["actions"]["Walking"] = {"mode": "sync"}
        self.assertEqual(self.evaluate(p)["A"]["strength"], 10)

    def test_random_clocks_are_channel_local(self):
        p = self.profile()
        for ch in ("A", "B"):
            p["channels"][ch].update(mode="random", random_waves=["ovc_breathe", "ovc_pulse"])
        p["channels"]["A"]["random_seconds"] = 1
        p["channels"]["B"]["random_seconds"] = 30
        rng = MagicMock(wraps=random.Random(5))
        planner = OvcPlanner(rng)
        first = self.evaluate(p, planner=planner, now=1)
        second = self.evaluate(p, planner=planner, now=1.5)
        self.assertEqual(first["A"]["token"], second["A"]["token"])
        third = self.evaluate(p, planner=planner, now=2.1)
        self.assertNotEqual(first["A"]["token"], third["A"]["token"])
        self.assertEqual(first["B"]["token"], third["B"]["token"])
        self.assertEqual(rng.choice.call_count, 3)

    def test_empty_random_pool_and_unknown_wave_fail_closed(self):
        p = self.profile()
        p["channels"]["A"].update(mode="random", random_waves=[])
        p["channels"]["B"].update(mode="fixed", wave="electrical_heartbeat")
        frame = self.evaluate(p)
        self.assertEqual((frame["A"]["strength"], frame["B"]["strength"]), (0, 0))

    def test_custom_envelope_is_encoded_as_vibration_not_electrical(self):
        p = sanitize_profile({"custom_waves": [{"key": "ovc_custom:1", "name": "Mine", "points": [0, 100] * 8}]})
        frames = wave_frames("ovc_custom:1", waveform_catalog(p))
        self.assertEqual(frames[0], "0A0A0A0A00000000")
        self.assertEqual(frames[1], "0A0A0A0A64646464")
        shared = [{"id": "Mine.json", "name": "Mine", "points": [80] * 16, "frequency": 240}]
        self.assertTrue(all(f.startswith("0A0A0A0A") for f in wave_frames("ovc_shared:Mine.json", waveform_catalog(p, shared))))

    def test_pause_gameover_stale_and_authorization_override_independent_mode(self):
        p = self.profile()
        for policy in p["channels"].values():
            policy.update(mode="fixed", strength=200)
        for packet in ({"paused": True}, {"systemMenuOpen": True}, {"gameOver": True}, {"timeScale": 0}):
            frame = self.evaluate(p, packet)
            self.assertEqual((frame["A"]["strength"], frame["B"]["strength"]), (0, 0))
        for kwargs in ({"fresh": False}, {"authorized": False}):
            frame = self.evaluate(p, **kwargs)
            self.assertEqual((frame["A"]["strength"], frame["B"]["strength"]), (0, 0))
        self.assertEqual(self.evaluate(p)["A"]["strength"], 30)

    def test_custom_names_and_keys_are_auto_numbered(self):
        b = Harness()
        self.assertEqual(b.saveOvcWaveform("", [10] * 16, ""), "ovc_custom:1")
        self.assertEqual(b.saveOvcWaveform("", [20] * 16, ""), "ovc_custom:2")
        self.assertEqual([w["name"] for w in b.ovc_profile["custom_waves"]], ["Custom Vibration 1", "Custom Vibration 2"])
        self.assertTrue(b.auto_output_enabled)
        b.bridge.emergency_stop.assert_not_called()

    def test_save_enforces_hard_cap_and_never_overwrites_coyote(self):
        b = Harness()
        profile = self.profile()
        profile["channels"]["A"]["strength"] = 40
        self.assertFalse(b.saveOvcProfile(profile))
        profile["channels"]["A"]["strength"] = 20
        self.assertTrue(b.saveOvcProfile(profile))
        self.assertEqual(set(b.persist.call_args.args[0]), {"ovc_profile"})
        self.assertTrue(b.auto_output_enabled)


if __name__ == "__main__":
    unittest.main()
