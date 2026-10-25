import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication
from qml_dashboard_prototype import backend as module
from manaka_wave_rules import WaveRule


class WorkbenchBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.patcher = patch.object(module, "app_data_dir", return_value=self.directory)
        self.patcher.start()
        self.backend = module.ControlCenterBackend(demo=True)

    def tearDown(self):
        self.backend.shutdown()
        self.patcher.stop()
        self.temp.cleanup()

    def test_strength_save_cannot_change_sources_waves_or_event_timing(self):
        old = self.backend.channelSettings
        raw = self.backend.channelSettings
        raw["A"]["maximum"] = 24
        raw["A"]["bindings"][0].update(source="heart", wave="official_tide", phase_ms=100)
        raw["A"]["climax"]["duration_ms"] = 4000
        self.assertTrue(self.backend.saveIntensitySettings(json.dumps(raw), self.backend.configurationRevision, False))
        saved = self.backend.channelSettings
        self.assertEqual(saved["A"]["maximum"], 24)
        self.assertEqual(saved["A"]["bindings"], old["A"]["bindings"])
        self.assertEqual(saved["A"]["climax"], old["A"]["climax"])

    def test_routing_save_preserves_calibration_and_synchronizes_event_timers(self):
        raw = self.backend.waveWorkbench
        raw["mapping"]["A"]["maximum"] = 99
        raw["mapping"]["A"]["hard_cap"] = 99
        raw["mapping"]["A"]["bindings"][0]["source"] = "heart"
        event = next(x for x in raw["policy"]["A"]["rules"] if x["source"] == "climax")
        event.update(duration_ms=2100, cooldown_ms=4000)
        result = self.backend.saveWaveWorkbench(json.dumps(raw))
        self.assertTrue(result["ok"], result)
        saved = self.backend.channelSettings
        self.assertEqual(saved["A"]["maximum"], 20)
        self.assertEqual(saved["A"]["hard_cap"], 30)
        self.assertEqual(saved["A"]["bindings"][0]["source"], "heart")
        self.assertEqual(saved["A"]["climax"]["duration_ms"], 2100)
        persisted = json.loads(module.config_path().read_text(encoding="utf-8"))
        self.assertEqual(persisted["wave_workbench"], self.backend.wave_policy.to_dict())

    def test_stale_drafts_do_not_overwrite_other_page_and_invalid_policy_is_atomic(self):
        draft = self.backend.waveWorkbench
        old_revision = self.backend.configurationRevision
        intensity = self.backend.channelSettings
        intensity["A"]["maximum"] = 21
        self.assertTrue(self.backend.saveIntensitySettings(json.dumps(intensity), old_revision, False))
        self.assertFalse(self.backend.saveWaveWorkbench(json.dumps(draft))["ok"])
        self.assertFalse(self.backend.saveIntensitySettings(json.dumps(intensity), old_revision, False))
        before = module.config_path().read_bytes()
        draft = self.backend.waveWorkbench
        draft["policy"]["A"]["default_wave"] = "library:missing"
        self.assertFalse(self.backend.saveWaveWorkbench(json.dumps(draft))["ok"])
        self.assertEqual(module.config_path().read_bytes(), before)

    def test_disk_failure_does_not_change_live_policy_or_intensity(self):
        draft = self.backend.waveWorkbench
        draft["policy"]["A"]["default_wave"] = "official_tide"
        before = self.backend.configurationRevision
        with patch.object(module, "update_config", side_effect=OSError("disk full")):
            self.assertFalse(self.backend.saveWaveWorkbench(json.dumps(draft))["ok"])
        self.assertEqual(self.backend.configurationRevision, before)

    def test_import_export_rename_duplicate_and_reference_safe_delete(self):
        frames = ["0A141E2801020304", "646E788205060708"]*17
        path = self.directory/"incoming.json"
        path.write_text(json.dumps(dict(name="Full waveform", frames=frames)), encoding="utf-8")
        result = self.backend.importWaveFile(path.as_uri())
        self.assertTrue(result["ok"], result)
        key = result["key"]
        asset = self.backend.waveAsset(key)
        self.assertEqual(asset["framesText"].splitlines(), frames)
        self.assertEqual(asset["durationMs"], 3400)
        self.assertEqual(self.backend._waveform_from_key(key).v3_frames(), tuple(frames))
        renamed = self.backend.saveWaveAsset(key, "Renamed", "My group", asset["framesText"])
        self.assertEqual(renamed["key"], key)
        self.assertTrue(self.backend.favoriteWaveAsset(key, True)["ok"])
        self.assertTrue(self.backend.waveAsset(key)["favorite"])
        export = self.directory/"exported.json"
        self.assertTrue(self.backend.exportWaveAsset(key, export.as_uri())["ok"])
        self.assertEqual(json.loads(export.read_text())["frames"], frames)
        copy = self.backend.duplicateWaveAsset(key)
        self.assertNotEqual(copy["key"], key)
        draft = self.backend.waveWorkbench
        draft["policy"]["B"]["default_wave"] = key
        self.assertTrue(self.backend.saveWaveWorkbench(json.dumps(draft))["ok"])
        self.assertFalse(self.backend.deleteWaveAsset(key)["ok"])
        self.assertTrue(self.backend.deleteWaveAsset(copy["key"])["ok"])
        self.assertFalse(self.backend.deleteWaveAsset("official_breath")["ok"])

    def test_malformed_collection_imports_nothing_and_failed_batch_rolls_back(self):
        path = self.directory/"bad.json"
        frame = "0A0A0A0A14141414"
        path.write_text(json.dumps(dict(waveforms=[dict(frames=[frame]), dict(frames=["FFFF"])])))
        self.assertFalse(self.backend.importWaveFile(str(path))["ok"])
        self.assertEqual(self.backend.custom_wave_library_value, [])
        path.write_text(json.dumps(dict(waveforms=[dict(frames=[frame]), dict(frames=[frame])])) )
        original = module.workbench.atomic_json
        count = 0
        def write(target, data):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError("disk full")
            original(target, data)
        with patch.object(module.workbench, "atomic_json", side_effect=write):
            self.assertFalse(self.backend.importWaveFile(str(path))["ok"])
        self.assertEqual(list(module.waveform_library_dir().glob("*.json")), [])

    def test_new_rows_and_reordering_keep_existing_strength_values(self):
        raw = self.backend.waveWorkbench
        first = raw["mapping"]["A"]["bindings"][0]
        raw["mapping"]["A"]["bindings"] = [dict(first, origin=-1, source="piston"), first]
        self.assertTrue(self.backend.saveWaveWorkbench(json.dumps(raw))["ok"])
        self.assertEqual(len(self.backend.channelSettings["A"]["bindings"]), 2)
        self.assertEqual(self.backend.channelSettings["A"]["bindings"][1]["weak"], 30)

    def test_old_custom_and_16_point_library_remain_available(self):
        directory = module.waveform_library_dir()
        directory.mkdir()
        (directory/"legacy.json").write_text(json.dumps(dict(name="Legacy", points=list(range(16)), frequency=92)))
        self.backend.custom_wave_library_value = self.backend._read_custom_wave_library()
        self.assertEqual(len(self.backend.waveAsset("library:legacy")["framesText"].splitlines()), 16)
        self.assertTrue(self.backend.waveAsset("custom")["ok"])

    def test_legacy_library_references_survive_reload_and_block_deletion(self):
        key=self.backend.duplicateWaveAsset("donor_piston")["key"]
        draft=self.backend.waveWorkbench
        draft["mapping"]["mode"]="legacy_v1"
        draft["legacy_wave"].update(mode="fixed",fixed=key)
        draft["legacy_wave"]["zones"]["peak"]=key
        draft["legacy_wave"]["actions"]["Walking"]=key
        self.assertTrue(self.backend.saveWaveWorkbench(json.dumps(draft))["ok"])
        self.assertFalse(self.backend.deleteWaveAsset(key)["ok"])
        restored=module.ControlCenterBackend(demo=True)
        try:
            self.assertEqual(restored.legacyWaveSettings,self.backend.legacyWaveSettings)
            self.assertEqual(restored._runtime_config().fixed_wave,key)
        finally: restored.shutdown()

    def test_legacy_and_new_wave_settings_both_roll_back_on_disk_error(self):
        before=self.backend.configurationRevision
        draft=self.backend.waveWorkbench
        draft["legacy_wave"].update(mode="fixed",fixed="donor_climax")
        draft["policy"]["A"]["default_wave"]="donor_piston"
        with patch.object(module,"update_config",side_effect=OSError("disk full")):
            self.assertFalse(self.backend.saveWaveWorkbench(json.dumps(draft))["ok"])
        self.assertEqual(self.backend.configurationRevision,before)
