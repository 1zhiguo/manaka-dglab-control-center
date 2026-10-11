import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QCoreApplication

import qml_dashboard_prototype.backend as backend_module
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
                backend = ControlCenterBackend(demo=True)
                try:
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


if __name__ == "__main__":
    unittest.main()
