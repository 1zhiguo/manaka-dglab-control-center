import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication

import qml_dashboard_prototype.backend as backend_module
from manaka_trigger_engine import TriggerFrame
from qml_dashboard_prototype.backend import ControlCenterBackend, waveform_file_stem


class WaveformLibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def test_filename_is_windows_safe(self):
        self.assertEqual(waveform_file_stem('  双击:"测试"  '), "双击__测试_")
        self.assertEqual(waveform_file_stem("..."), "未命名波形")

    def test_named_waveform_can_be_saved_loaded_and_deleted(self):
        points = [0, 10, 30, 60, 100, 60, 30, 10, 0, 10, 30, 60, 100, 60, 30, 0]
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary:
            library = Path(temporary) / "waveforms"
            with (
                patch.object(backend_module, "waveform_library_dir", return_value=library),
                patch.object(backend_module, "load_config", return_value={}),
                patch.object(backend_module, "update_config"),
            ):
                backend = ControlCenterBackend(demo=True, language="zh")
                try:
                    self.assertEqual(backend.nextCustomWaveformName, "自定义波形 1")
                    self.assertTrue(backend.saveCustomWaveform("双峰测试", points, 110))
                    self.assertEqual(len(backend.savedCustomWaveforms), 1)
                    entry = backend.savedCustomWaveforms[0]
                    self.assertEqual(entry["name"], "双峰测试")
                    self.assertEqual(entry["points"], points)
                    self.assertEqual(entry["frequency"], 110)

                    backend.custom_points_value = [0] * 16
                    self.assertTrue(backend.loadCustomWaveform(entry["id"]))
                    self.assertEqual(backend.customPoints, points)
                    self.assertEqual(backend.customName, "双峰测试")

                    self.assertTrue(backend.deleteCustomWaveform(entry["id"]))
                    self.assertEqual(backend.savedCustomWaveforms, [])
                finally:
                    backend.poll_timer.stop()

    def test_automatic_names_keep_one_sequence_across_languages(self):
        points = [0, 10, 30, 60, 100, 60, 30, 10, 0, 10, 30, 60, 100, 60, 30, 0]
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary:
            library = Path(temporary) / "waveforms"
            with (
                patch.object(backend_module, "waveform_library_dir", return_value=library),
                patch.object(backend_module, "load_config", return_value={}),
                patch.object(backend_module, "update_config"),
            ):
                backend = ControlCenterBackend(demo=True, language="zh")
                try:
                    self.assertTrue(backend.saveCustomWaveform("", points, 92))
                    self.assertEqual(backend.customName, "自定义波形 1")
                    self.assertEqual(backend.nextCustomWaveformName, "自定义波形 2")

                    backend.setLanguage("en")
                    self.assertEqual(backend.nextCustomWaveformName, "Custom Wave 2")
                    self.assertTrue(backend.saveCustomWaveform("", points, 92))
                    self.assertEqual(backend.customName, "Custom Wave 2")
                    self.assertEqual(backend.nextCustomWaveformName, "Custom Wave 3")
                finally:
                    backend.poll_timer.stop()

    def test_action_wave_mapping_supports_official_and_library_waves(self):
        points = [0, 10, 30, 60, 100, 60, 30, 10, 0, 10, 30, 60, 100, 60, 30, 0]
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary:
            library = Path(temporary) / "waveforms"
            with (
                patch.object(backend_module, "waveform_library_dir", return_value=library),
                patch.object(backend_module, "load_config", return_value={}),
                patch.object(backend_module, "update_config"),
            ):
                backend = ControlCenterBackend(demo=True, language="zh")
                try:
                    self.assertTrue(backend.setActionWaveform("Dogeza", "official_tide"))
                    mapping = next(item for item in backend.actionWaveMappings if item["action"] == "Dogeza")
                    self.assertEqual(mapping["waveKey"], "official_tide")
                    self.assertEqual(mapping["actionLabel"], "土下座")
                    self.assertTrue(mapping["isOverride"])

                    self.assertTrue(backend.saveCustomWaveform("动作测试", points, 110))
                    custom_key = backend.savedCustomWaveforms[0]["key"]
                    self.assertTrue(backend.setActionWaveform("OnaniNormal", custom_key))
                    self.assertEqual(backend._selected_action_wave_key("OnaniNormal"), custom_key)
                finally:
                    backend.poll_timer.stop()

    def test_smart_b_channel_switches_from_action_type_only(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary:
            library = Path(temporary) / "waveforms"
            with (
                patch.object(backend_module, "waveform_library_dir", return_value=library),
                patch.object(backend_module, "load_config", return_value={}),
                patch.object(backend_module, "update_config"),
            ):
                backend = ControlCenterBackend(demo=True, language="zh")
                frame = TriggerFrame(0, 24, "idle", "action-ramp", "test", ())
                try:
                    backend.action_value = "PickUpItem"
                    backend._show_frame(frame)
                    self.assertIsNone(backend.current_wave_b)
                    self.assertEqual(backend.current_output_b, 0)

                    backend.action_value = "Dogeza"
                    backend._show_frame(frame)
                    self.assertEqual(backend.current_wave_b.key, "official_breath")

                    backend.setActionWaveform("Dogeza", "official_tide")
                    backend._show_frame(frame)
                    self.assertEqual(backend.current_wave_b.key, "official_tide")
                finally:
                    backend.poll_timer.stop()


if __name__ == "__main__":
    unittest.main()
