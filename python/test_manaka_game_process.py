import queue
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from manaka_game_process import GAME_EXE, matching_game
from qml_dashboard_prototype import backend as module


class GameProcessTests(unittest.TestCase):
    def test_only_exact_game_executable_matches(self):
        self.assertEqual(matching_game([(10, GAME_EXE+".bak", ""), (11, "SecretFlasherManakaLauncher.exe", "")]), 0)
        self.assertEqual(matching_game([(12, GAME_EXE.upper(), "")]), 12)

    def test_selected_installation_path_is_case_insensitive_and_normalized(self):
        processes = [(1, GAME_EXE, "D:/Other/"+GAME_EXE), (2, GAME_EXE, "c:/mygame/"+GAME_EXE)]
        self.assertEqual(matching_game(processes, "C:\\MyGame\\"), 2)
        self.assertEqual(matching_game(processes, "C:/Different"), 0)

    def test_unknown_executable_path_does_not_claim_selected_installation(self):
        self.assertEqual(matching_game([(1, GAME_EXE, "")], "C:/MyGame"), 0)
        self.assertEqual(matching_game([(1, GAME_EXE, "")]), 1)

    def harness(self):
        return SimpleNamespace(demo_mode=False, _game_probe_active=False, _next_game_probe=0,
            game_folder_value="C:/Game", game_running_value=False, gameProcessChanged=MagicMock(), messages=queue.Queue(),
            auto_output_enabled=False, ovc_enabled=False)

    def test_probe_is_background_throttled_and_cannot_authorize_output(self):
        b = self.harness()
        with patch.object(module.time, "monotonic", return_value=10), patch.object(module.threading, "Thread") as thread:
            module.ControlCenterBackend._poll_game_process(b)
            module.ControlCenterBackend._poll_game_process(b)
            thread.assert_called_once()
            self.assertTrue(thread.call_args.kwargs["daemon"])
            with patch.object(module, "find_game_process", return_value=42):
                thread.call_args.kwargs["target"]()
        _, result = b.messages.get_nowait()
        module.ControlCenterBackend._apply_game_process_result(b, result)
        self.assertTrue(b.game_running_value)
        self.assertFalse(b.auto_output_enabled or b.ovc_enabled)
        b._game_probe_active = False
        with patch.object(module.time, "monotonic", return_value=11), patch.object(module.threading, "Thread") as thread:
            module.ControlCenterBackend._poll_game_process(b)
            thread.assert_not_called()

    def test_process_exit_clears_highlight_and_old_folder_result_is_ignored(self):
        b = self.harness(); b.game_running_value = True
        module.ControlCenterBackend._apply_game_process_result(b, {"folder":"C:/Game","running":False})
        self.assertFalse(b.game_running_value)
        b.gameProcessChanged.emit.assert_called_once()
        module.ControlCenterBackend._apply_game_process_result(b, {"folder":"C:/Old","running":True})
        self.assertFalse(b.game_running_value)
        b.gameProcessChanged.emit.assert_called_once()

    def test_demo_and_probe_failure_do_not_scan_or_claim_running(self):
        b = self.harness(); b.demo_mode = True
        with patch.object(module.threading, "Thread") as thread:
            module.ControlCenterBackend._poll_game_process(b)
            thread.assert_not_called()
        b.demo_mode = False
        with patch.object(module.threading, "Thread") as thread:
            module.ControlCenterBackend._poll_game_process(b)
            with patch.object(module, "find_game_process", side_effect=OSError("exited")):
                thread.call_args.kwargs["target"]()
        _, result = b.messages.get_nowait()
        self.assertFalse(result["running"])


if __name__ == "__main__":
    unittest.main()
