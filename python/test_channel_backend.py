import json
from pathlib import Path
import tempfile
import unittest
import threading
import time
from unittest.mock import patch, Mock

from PySide6.QtCore import QCoreApplication
from qml_dashboard_prototype import backend as module
from manaka_channel_engine import MappingSettings


class ChannelBackendTests(unittest.TestCase):
    def test_fresh_profile_uses_donor_sources_but_existing_profiles_are_not_overwritten(self):
        fresh = module.migrate_settings({"theme":"light"})
        self.assertEqual(fresh.mode, "independent")
        self.assertEqual(fresh.A.device, "vibrator")
        self.assertEqual(fresh.B.device, "piston")
        self.assertEqual(fresh.A.bindings[0].source, "device")
        self.assertEqual(fresh.B.bindings[0].source, "device")
        old = module.migrate_settings(dict(trigger_bpm=95, full_bpm=150, output_max=18))
        self.assertEqual(old.mode, "legacy_v1")
        self.assertEqual(old.A.maximum, 18)
        self.assertEqual(old.A.bindings[0].low, 95)
        self.assertEqual(module.migrate_settings({"channel_mapping":old.to_dict()}), old)

    def test_legacy_preview_uses_unsaved_draft_ranges(self):
        settings = self.backend.channelSettings
        settings["mode"] = "legacy_v1"
        settings["legacy"].update(min_strength=0, output_max=10)
        result = self.backend.previewChannelSettings(json.dumps(settings), json.dumps(
            dict(stage="Residence", heartRate=160, monotonicMs=10000, action="Test")))
        self.assertEqual(result["error"], "")
        self.assertEqual(result["A"], 10)
        self.assertNotEqual(self.backend.outputMax, 10)

    def test_unified_save_retains_both_generations_and_is_atomic_on_invalid_legacy(self):
        settings = self.backend.channelSettings
        settings["mode"] = "legacy_v1"
        settings["legacy"].update(trigger_bpm=95, full_bpm=150, min_strength=3, output_max=17)
        settings["B"]["maximum"] = 23
        self.assertTrue(self.backend.saveChannelSettings(json.dumps(settings)))
        self.assertEqual(self.backend.outputMax, 17)
        self.assertEqual(self.backend.channelSettings["B"]["maximum"], 23)
        saved = json.loads(module.config_path().read_text(encoding="utf-8"))
        self.assertEqual(saved["trigger_bpm"], 95)
        self.assertEqual(saved["channel_mapping"]["B"]["maximum"], 23)
        settings["legacy"]["full_bpm"] = 90
        with patch.object(module, "update_config") as persist:
            self.assertFalse(self.backend.saveChannelSettings(json.dumps(settings)))
            persist.assert_not_called()
        self.assertEqual(self.backend.fullBpm, 150)

    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.patches = [patch.object(module, "app_data_dir", return_value=Path(self.directory.name)),
                        patch.object(module, "load_config", return_value={})]
        for item in self.patches:
            item.start()
        self.backend = module.ControlCenterBackend(demo=True)

    def tearDown(self):
        self.backend.shutdown()
        for item in reversed(self.patches):
            item.stop()
        self.directory.cleanup()

    def test_preview_is_isolated_and_missing_data_is_visible(self):
        self.backend.bridge = Mock()
        current_engine = self.backend.channel_engine
        settings = MappingSettings().to_dict()
        settings["A"]["bindings"][0]["source"] = "vibrator"
        result = self.backend.previewChannelSettings(json.dumps(settings), json.dumps(dict(stage="Residence",ecstasy=.5,action="Test")))
        self.assertEqual(result["A"], 0)
        self.assertEqual(result["missingA"], ["vibrator"])
        self.assertIs(self.backend.channel_engine, current_engine)
        self.backend.bridge.update_auto_outputs.assert_not_called()
        self.backend.bridge.emergency_stop.assert_not_called()

    def test_save_roundtrips_and_resets_output(self):
        settings = MappingSettings().to_dict()
        self.assertTrue(self.backend.saveChannelSettings(json.dumps(settings)))
        self.assertEqual(self.backend.channelSettings["mode"], "independent")
        self.assertEqual((self.backend.outputA, self.backend.outputB), (0, 0))
        data = json.loads(module.config_path().read_text(encoding="utf-8"))["channel_mapping"]
        self.assertEqual(MappingSettings.parse(data), MappingSettings.parse(settings))
        self.assertIsInstance(self.backend.channelSettings["A"]["bindings"],list)

    def test_raising_cap_requires_existing_confirmation(self):
        settings = MappingSettings().to_dict()
        settings["A"]["hard_cap"] = 60
        self.assertFalse(self.backend.saveChannelSettings(json.dumps(settings), False))
        self.assertTrue(self.backend.saveChannelSettings(json.dumps(settings), True))

    def test_draft_validation_is_localized_and_has_no_side_effects(self):
        settings = MappingSettings().to_dict()
        settings["B"]["minimum"] = 50
        self.backend.language_name = "en"
        before = self.backend.channelSettings
        with patch.object(module, "update_config") as persist:
            result = self.backend.validateChannelSettings(json.dumps(settings))
            self.assertFalse(result["valid"])
            self.assertIn("B:", result["error"])
            self.assertIn("minimum", result["error"])
            self.assertFalse(self.backend.saveChannelSettings(json.dumps(settings)))
            persist.assert_not_called()
        self.assertEqual(self.backend.channelSettings, before)
        self.backend.language_name = "zh"
        self.assertIn("日常最低", self.backend.validateChannelSettings(json.dumps(settings))["error"])

    def test_draft_validation_explains_event_and_source_constraints(self):
        settings = MappingSettings().to_dict()
        self.backend.language_name = "en"
        settings["A"]["failure"]["duration_ms"] = 2000
        settings["A"]["failure"]["cooldown_ms"] = 1000
        self.assertIn("Cooldown", self.backend.validateChannelSettings(json.dumps(settings))["error"])
        settings["A"]["failure"]["cooldown_ms"] = 5000
        settings["A"]["bindings"][0].update(source="piston",weak=70,medium=20)
        self.assertIn("percentages", self.backend.validateChannelSettings(json.dumps(settings))["error"])
        settings["A"]["bindings"][0].update(source="vibrator",weak=30)
        self.assertTrue(self.backend.validateChannelSettings(json.dumps(settings))["valid"])

    def test_development_build_can_update_plugin_without_bundled_interop(self):
        root = Path(self.directory.name)
        game = root/"game"
        game.mkdir()
        source = root/"ManakaDGLabTelemetry.dll"
        source.write_bytes(b"new-plugin")
        with patch.object(module,"validate_game_folder",return_value=(True,"valid")), \
             patch.object(module,"validate_supported_game_build",return_value=(True,"v1.1.3")), \
             patch.object(module,"game_build_fingerprint",return_value="test"), \
             patch.object(module,"uses_bundled_v113_interop",return_value=True), \
             patch.object(module,"bepinex_runtime_issue",return_value=None), \
             patch.object(module,"provision_bepinex_runtime") as provision:
            result = module.install_plugin_payload(game,source,root/"missing-runtime")
            provision.assert_not_called()
        self.assertEqual(result["action"],"unchanged")
        self.assertEqual((game/"BepInEx/plugins/ManakaDGLabTelemetry/ManakaDGLabTelemetry.dll").read_bytes(),b"new-plugin")

    def test_file_job_runs_in_background_and_applies_result_on_gui_thread(self):
        threads = []
        main_thread = threading.get_ident()
        def work():
            threads.append(threading.get_ident())
            time.sleep(.1)
            return "complete"
        def finish(result):
            threads.append(threading.get_ident())
            self.assertEqual(result, "complete")
        start = time.perf_counter()
        self.assertTrue(self.backend._begin_file_job(work, finish))
        self.assertLess(time.perf_counter()-start, .08)
        self.assertTrue(self.backend.fileJobBusy)
        self.assertFalse(self.backend._begin_file_job(work,finish))
        deadline = time.monotonic()+2
        while self.backend.fileJobBusy and time.monotonic()<deadline:
            self.app.processEvents()
            time.sleep(.005)
        self.assertFalse(self.backend.fileJobBusy)
        self.assertNotEqual(threads[0], main_thread)
        self.assertEqual(threads[1], main_thread)

    def test_one_change_between_ui_refresh_intervals_is_not_lost(self):
        self.backend.demo_mode = False
        self.backend.ui_page_index = 0
        self.backend.ui_last_telemetry_emit = time.monotonic()
        emitted = []
        self.backend.vitalsChanged.connect(lambda: emitted.append(True))
        self.backend.messages.put(("telemetry",dict(stage="Residence", heartRate=115,monotonicMs=10,action="None")))
        self.backend._poll()
        self.assertEqual(emitted, [])
        self.backend.ui_last_telemetry_emit = 0
        self.backend._poll()
        self.assertEqual(emitted, [True])
