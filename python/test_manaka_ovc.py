import queue
import time
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Signal
from manaka_devices.ovc import plan, sanitize_profile, step_strength, vibration_mode
from qml_dashboard_prototype.v4_integration import V4DeviceBackend
from qml_dashboard_prototype import backend as backend_module


class Harness(V4DeviceBackend):
    statusChanged = Signal()
    connectionChanged = Signal()
    outputChanged = Signal()

    def __init__(self):
        super().__init__()
        self.persist = MagicMock()
        self._init_device_support({"socket_protocol":"v4"}, self.persist)
        self.demo_mode = False
        self.language_name = "en"
        self.last_packet = {"vibration": "Low", "stage": "Stage02"}
        self.last_receive = time.monotonic()
        self.auto_output_enabled = True
        self.device_connected_value = True
        self.bridge = MagicMock()
        self.v4_hub = MagicMock()
        self.messages = queue.Queue()
        self.ovc_connected = True
        self._log = MagicMock()
        self._toast = MagicMock()

    @property
    def telemetryOnline(self):
        return bool(self.last_receive and time.monotonic() - self.last_receive < .5)


class OvcMappingTests(unittest.TestCase):
    def test_verified_game_enum_and_unknown_fail_closed(self):
        for raw, mode in (("Off", "off"), ("Low", "low"), ("High", "high"), ("Random", "random"), ("Edging", "unknown")):
            self.assertEqual(vibration_mode(raw), mode)

    def test_step_floor_and_finite_validation(self):
        for value, cap, result in ((38, 200, 30), (200, 25, 20), (9, 200, 0), (210, 200, 200), (float("nan"), 30, 0)):
            self.assertEqual(step_strength(value, cap), result)

    def test_only_game_vibrator_drives_output(self):
        profile = sanitize_profile({})
        for raw, value in (("Off", 0), ("Low", 10), ("High", 30), ("Random", 0), ("Invalid", 0)):
            result = plan({"vibration": raw, "stage": "Stage02", "heartRate": 160, "orgasm": True}, profile, fresh=True, authorized=True)
            self.assertEqual(result[1:3], (value, 0))

    def test_all_safety_gates_override_high(self):
        packet = {"vibration": "High", "stage": "Stage02"}
        for patch in ({"paused": True}, {"systemMenuOpen": True}, {"gameOver": True}, {"stage": "None"}, {"timeScale": 0}, {"managedTimeScale": 0}):
            self.assertEqual(plan({**packet, **patch}, sanitize_profile({}), fresh=True, authorized=True)[1:3], (0, 0))
        for fresh, armed in ((False, True), (True, False)):
            self.assertEqual(plan(packet, sanitize_profile({}), fresh=fresh, authorized=armed)[1:3], (0, 0))

    def test_profile_is_own_subtree_with_no_electrical_values(self):
        original = {"hard_cap": 25, "low": 100, "channel_b": True, "wave_map": {"peak": "climax"}}
        clean = sanitize_profile(original)
        self.assertEqual((clean["hard_cap"], clean["low"]), (20, 20))
        self.assertNotIn("wave_map", clean)
        self.assertEqual(original["hard_cap"], 25)


class OvcIntegrationTests(unittest.TestCase):
    def test_connect_does_not_authorize(self):
        b = Harness()
        b.ovc_enabled = True
        b.v4_messages.put(("dglab", {"role": "ovc", "event": "connected"}))
        b._poll_device_support()
        self.assertFalse(b.ovc_enabled)
        self.assertTrue(b.ovc_connected)
        self.assertEqual(b.ovc_output, (0, 0))
        b.v4_hub.channel.return_value.set_auto_enabled.assert_not_called()

    def test_ovc_failure_never_stops_coyote(self):
        b = Harness()
        b.v4_messages.put(("dglab", {"role": "ovc", "event": "disconnected"}))
        b._poll_device_support()
        self.assertTrue(b.auto_output_enabled)
        b.bridge.emergency_stop.assert_not_called()

    def test_stale_telemetry_waits_at_zero_until_new_fresh_data(self):
        b = Harness()
        b.ovc_enabled = True
        b.last_receive = time.monotonic() - 1
        b._sync_ovc(force=True)
        self.assertTrue(b.ovc_enabled and b.ovc_waiting_for_game)
        self.assertEqual(b.ovc_output, (0, 0))
        b.v4_hub.channel.return_value.set_auto_enabled.assert_not_called()
        with patch("qml_dashboard_prototype.v4_integration.time.monotonic", return_value=b.ovc_resume_after+.1):
            b.last_receive = time.monotonic()
            b._sync_ovc(force=True)
        self.assertTrue(b.ovc_enabled)
        self.assertFalse(b.ovc_waiting_for_game)
        self.assertEqual(b.ovc_output, (10, 0))

    def test_save_is_independent_and_disarms_only_ovc(self):
        b = Harness()
        self.assertTrue(b.saveOvcSettings(10, 20, 30, 30, True, False))
        self.assertEqual(set(b.persist.call_args.args[0]), {"ovc_profile"})
        self.assertTrue(b.auto_output_enabled)
        b.bridge.emergency_stop.assert_not_called()
        self.assertFalse(b.ovc_enabled)

    def test_failed_save_leaves_running_state_unchanged(self):
        b = Harness()
        b.ovc_enabled = True
        b.persist.side_effect = OSError("disk full")
        self.assertFalse(b.saveOvcSettings(0, 0, 0, 0, False, False))
        self.assertTrue(b.ovc_enabled)
        self.assertEqual(b.ovc_profile["high"], 30)

    def test_global_stop_covers_both_routes(self):
        b = Harness()
        b.ovc_enabled = True
        b.emergencyStopAll()
        self.assertFalse(b.ovc_enabled)
        self.assertFalse(b.auto_output_enabled)
        b.bridge.emergency_stop.assert_called_once()
        b.v4_hub.latch_global_emergency_stop.assert_called_once()


class DeviceConfigTests(unittest.TestCase):
    def test_merge_preserves_electrical_wave_and_game_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "config.json"
            original = {"hard_cap": 50, "wave_map": {"low": "custom"}, "game_folder": "C:/Game"}
            target.write_text(json.dumps(original), encoding="utf-8")
            with patch.object(backend_module, "config_path", return_value=target):
                backend_module.update_device_config({"ovc_profile": sanitize_profile({})})
            updated = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual({key: updated[key] for key in original}, original)
            self.assertEqual(updated["ovc_profile"]["hard_cap"], 30)

    def test_failed_replace_preserves_original_and_removes_own_temp(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "config.json"
            original = b'{"hard_cap":50}'
            target.write_bytes(original)
            with patch.object(backend_module, "config_path", return_value=target), patch.object(backend_module.os, "replace", side_effect=OSError("disk error")):
                with self.assertRaises(OSError):
                    backend_module.update_device_config({"socket_protocol": "v4"})
            self.assertEqual(target.read_bytes(), original)
            self.assertEqual(list(Path(tmp).glob("*.tmp")), [])

    def test_invalid_existing_config_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "config.json"
            target.write_bytes(b'{broken json')
            with patch.object(backend_module, "config_path", return_value=target):
                with self.assertRaises(OSError):
                    backend_module.update_device_config({"socket_protocol": "v4"})
            self.assertEqual(target.read_bytes(), b'{broken json')


if __name__ == "__main__":
    unittest.main()
