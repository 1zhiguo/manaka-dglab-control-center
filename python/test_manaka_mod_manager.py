import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from manaka_mod_manager import ManakaModManager, ModManagerError


class ManakaModManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        base = Path(self.temp.name)
        self.game = base / "game"
        self.source = base / "pack"
        self.game.mkdir()
        self.source.mkdir()
        (self.game / "SecretFlasherManaka.exe").write_bytes(b"test")

    def tearDown(self) -> None:
        self.temp.cleanup()

    @patch("manaka_mod_manager.game_is_running", return_value=False)
    def test_plugin_install_disable_and_restore(self, _running) -> None:
        source_plugin = self.source / "BepInEx" / "plugins" / "BetterCompass.dll"
        source_plugin.parent.mkdir(parents=True)
        source_plugin.write_bytes(b"plugin")
        manager = ManakaModManager(self.game, self.source)
        item = next(item for item in manager.scan() if item["name"] == "BetterCompass")
        self.assertEqual(item["status"], "可安装")

        manager.set_enabled(item["id"], True)
        target = self.game / "BepInEx" / "plugins" / "BetterCompass.dll"
        self.assertEqual(target.read_bytes(), b"plugin")

        manager.set_enabled(item["id"], False)
        self.assertFalse(target.exists())
        self.assertTrue(target.with_name("BetterCompass.dll.disabled").exists())

        manager.set_enabled(item["id"], True)
        self.assertTrue(target.exists())

    @patch("manaka_mod_manager.game_is_running", return_value=False)
    def test_local_plugin_disable_and_restore_when_game_is_source(self, _running) -> None:
        target = self.game / "BepInEx" / "plugins" / "NPCBehaviorModifier.dll"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"local-plugin")
        manager = ManakaModManager(self.game, self.game)

        item = next(item for item in manager.scan() if item["name"] == "NPCBehaviorModifier")
        manager.set_enabled(item["id"], False)
        disabled = target.with_name("NPCBehaviorModifier.dll.disabled")
        self.assertFalse(target.exists())
        self.assertEqual(disabled.read_bytes(), b"local-plugin")

        item = next(item for item in manager.scan() if item["name"] == "NPCBehaviorModifier")
        manager.set_enabled(item["id"], True)
        self.assertEqual(target.read_bytes(), b"local-plugin")
        self.assertFalse(disabled.exists())

    @patch("manaka_mod_manager.game_is_running", return_value=False)
    def test_saved_plugin_is_installed_to_plugin_root(self, _running) -> None:
        source_plugin = self.source / "BepInEx" / "plugins" / "save" / "Freer.dll"
        source_plugin.parent.mkdir(parents=True)
        source_plugin.write_bytes(b"saved")
        manager = ManakaModManager(self.game, self.source)
        item = manager.scan()[0]
        manager.set_enabled(item["id"], True)
        self.assertTrue((self.game / "BepInEx" / "plugins" / "Freer.dll").is_file())

    @patch("manaka_mod_manager.game_is_running", return_value=False)
    def test_v1_group_is_moved_without_deletion(self, _running) -> None:
        source = self.source / "CustomMissions1"
        source.mkdir()
        (source / "Brat_1.json").write_text("{}", encoding="utf-8")
        (source / "Brat_2.json").write_text("{}", encoding="utf-8")
        manager = ManakaModManager(self.game, self.source)
        item = next(item for item in manager.scan() if item["name"] == "Brat")
        self.assertEqual(item["fileCount"], 2)
        manager.set_enabled(item["id"], True)
        self.assertEqual(len(list((self.game / "CustomMissions").glob("*.json"))), 2)
        manager.set_enabled(item["id"], False)
        self.assertEqual(len(list((self.game / "CustomMissions").glob("*.json"))), 0)
        self.assertEqual(len(list((self.game / "ManakaModManager" / "disabled" / "v1").glob("*.json"))), 2)

    @patch("manaka_mod_manager.game_is_running", return_value=False)
    def test_nested_v1_pack_is_scanned_and_toggled_with_folder_preserved(self, _running) -> None:
        active = self.game / "CustomMissions" / "challenges"
        active.mkdir(parents=True)
        (active / "challenges.json").write_text("{}", encoding="utf-8")
        (active / "bonus.json").write_text("{}", encoding="utf-8")

        manager = ManakaModManager(self.game, self.source)
        item = next(item for item in manager.scan() if item["name"] == "challenges")
        self.assertEqual(item["fileCount"], 2)
        self.assertEqual(item["status"], "已启用")

        manager.set_enabled(item["id"], False)
        self.assertFalse((active / "challenges.json").exists())
        self.assertTrue(
            (self.game / "ManakaModManager" / "disabled" / "v1" / "challenges" / "challenges.json").is_file()
        )

        item = next(item for item in manager.scan() if item["name"] == "challenges")
        manager.set_enabled(item["id"], True)
        self.assertTrue((active / "challenges.json").is_file())

    @patch("manaka_mod_manager.game_is_running", return_value=False)
    def test_v2_folder_toggle_preserves_contents(self, _running) -> None:
        source = self.source / "CustomMissions2" / "HideAndSeek"
        source.mkdir(parents=True)
        (source / "main.code").write_text("code", encoding="utf-8")
        manager = ManakaModManager(self.game, self.source)
        item = next(item for item in manager.scan() if item["kind"] == "v2")
        manager.set_enabled(item["id"], True)
        active = self.game / "CustomMissions2" / "HideAndSeek"
        self.assertEqual((active / "main.code").read_text(encoding="utf-8"), "code")
        manager.set_enabled(item["id"], False)
        self.assertFalse(active.exists())
        self.assertTrue((self.game / "ManakaModManager" / "disabled" / "v2" / "HideAndSeek" / "main.code").is_file())

    @patch("manaka_mod_manager.game_is_running", return_value=False)
    def test_known_v2_variants_are_mutually_exclusive(self, _running) -> None:
        for name in ("Aftermath", "Aftermath&StageLock"):
            folder = self.source / "CustomMissions2" / name
            folder.mkdir(parents=True)
            (folder / "main.code").write_text("code", encoding="utf-8")
        manager = ManakaModManager(self.game, self.source)
        items = {item["name"]: item for item in manager.scan()}
        manager.set_enabled(items["Aftermath"]["id"], True)
        with self.assertRaises(ModManagerError):
            manager.set_enabled(items["Aftermath&StageLock"]["id"], True)

    @patch("manaka_mod_manager.game_is_running", return_value=True)
    def test_refuses_changes_while_game_is_running(self, _running) -> None:
        source_plugin = self.source / "BepInEx" / "plugins" / "BetterCompass.dll"
        source_plugin.parent.mkdir(parents=True)
        source_plugin.write_bytes(b"plugin")
        manager = ManakaModManager(self.game, self.source)
        item = manager.scan()[0]
        with self.assertRaises(ModManagerError):
            manager.set_enabled(item["id"], True)

    def test_scans_three_repository_hub_layout(self) -> None:
        plugin = self.source / "plugins" / "files" / "BetterCompass.dll"
        plugin.parent.mkdir(parents=True)
        plugin.write_bytes(b"plugin")
        v1 = self.source / "custommissions1" / "files" / "Brat_1.json"
        v1.parent.mkdir(parents=True)
        v1.write_text("{}", encoding="utf-8")
        v2 = self.source / "custommissions2" / "files" / "HideAndSeek" / "main.code"
        v2.parent.mkdir(parents=True)
        v2.write_text("code", encoding="utf-8")

        inventory = ManakaModManager(self.game, self.source).scan()
        self.assertEqual({item["kind"] for item in inventory}, {"plugin", "v1", "v2"})

    def test_9527_usage_categories_are_exposed_for_filters(self) -> None:
        plugin_root = self.source / "BepInEx" / "plugins"
        plugin_root.mkdir(parents=True)
        for name in ("SFM_custom_mission.dll", "BetterCompass.dll"):
            (plugin_root / name).write_bytes(b"plugin")
        v1 = self.source / "CustomMissions" / "admirer.json"
        v1.parent.mkdir(parents=True)
        v1.write_text("{}", encoding="utf-8")
        for name in ("blackmailV2", "Moaning3", "HideAndSeek"):
            folder = self.source / "CustomMissions2" / name
            folder.mkdir(parents=True)
            (folder / "main.code").write_text("code", encoding="utf-8")

        inventory = ManakaModManager(self.game, self.source).scan()
        categories = {item["name"].casefold(): item["category"] for item in inventory}

        self.assertEqual(categories["sfm_custom_mission"], "core")
        self.assertEqual(categories["bettercompass"], "utility")
        self.assertEqual(categories["admirer"], "v1")
        self.assertEqual(categories["blackmailv2"], "v2_story")
        self.assertEqual(categories["moaning3"], "media")
        self.assertEqual(categories["hideandseek"], "gameplay")

    def test_v2_category_uses_folder_name_instead_of_localized_meta_title(self) -> None:
        folder = self.source / "CustomMissions2" / "blackmailV2"
        folder.mkdir(parents=True)
        (folder / "main.code").write_text("code", encoding="utf-8")
        (folder / "meta.json").write_text(
            '{"title":{"Sc":"本地化后的任意标题"},"description":{"Sc":"剧情任务"}}',
            encoding="utf-8",
        )

        item = next(
            item for item in ManakaModManager(self.game, self.source).scan()
            if item["kind"] == "v2"
        )

        self.assertEqual(item["name"], "本地化后的任意标题")
        self.assertEqual(item["classificationKey"], "blackmailV2")
        self.assertEqual(item["category"], "v2_story")

    @patch("manaka_mod_manager.game_is_running", return_value=False)
    def test_mission_entries_report_their_loader_dependency(self, _running) -> None:
        plugin_root = self.source / "BepInEx" / "plugins"
        plugin_root.mkdir(parents=True)
        (plugin_root / "SFM_custom_mission.dll").write_bytes(b"v1-loader")
        (plugin_root / "SFM_custom_mission_v2.dll").write_bytes(b"v2-loader")
        v1 = self.source / "CustomMissions1" / "Sample.json"
        v1.parent.mkdir(parents=True)
        v1.write_text("{}", encoding="utf-8")
        v2 = self.source / "CustomMissions2" / "Moaning2" / "main.code"
        v2.parent.mkdir(parents=True)
        v2.write_text("code", encoding="utf-8")

        manager = ManakaModManager(self.game, self.source)
        inventory = manager.scan()
        v1_item = next(item for item in inventory if item["kind"] == "v1")
        v2_item = next(item for item in inventory if item["kind"] == "v2")
        self.assertEqual(v1_item["requiredPluginName"], "CustomMission 1")
        self.assertEqual(v2_item["requiredPluginName"], "CustomMission 2")
        self.assertTrue(v1_item["dependencyAvailable"])
        self.assertFalse(v2_item["dependencyReady"])

        loader = next(item for item in inventory if item["id"] == "plugin|SFM_custom_mission_v2.dll")
        manager.set_enabled(loader["id"], True)
        v2_item = next(item for item in manager.scan() if item["kind"] == "v2")
        self.assertTrue(v2_item["dependencyReady"])

    @patch("manaka_mod_manager.game_is_running", return_value=False)
    def test_hub_installs_required_game_root_assets(self, _running) -> None:
        plugin_root = self.source / "plugins" / "files"
        (plugin_root / "save").mkdir(parents=True)
        (plugin_root / "save" / "NPCBehaviorModifier.dll").write_bytes(b"npc")
        (plugin_root / "SFM_custom_mission.dll").write_bytes(b"loader")
        assets = plugin_root / "_game_root"
        (assets / "NPCBehaviorMod").mkdir(parents=True)
        (assets / "NPCBehaviorMod" / "config.txt").write_text("config", encoding="utf-8")
        (assets / "NotoSerifSC-Regular.otf").write_bytes(b"font")

        manager = ManakaModManager(self.game, self.source)
        items = {item["name"]: item for item in manager.scan()}
        manager.set_enabled(items["NPCBehaviorModifier"]["id"], True)
        manager.set_enabled(items["SFM_custom_mission"]["id"], True)
        self.assertTrue((self.game / "NPCBehaviorMod" / "config.txt").is_file())
        self.assertEqual((self.game / "NotoSerifSC-Regular.otf").read_bytes(), b"font")

    @patch("manaka_mod_manager.game_is_running", return_value=False)
    def test_same_name_dropin_refreshes_enabled_plugin(self, _running) -> None:
        dropin = Path(self.temp.name) / "dropin" / "BepInEx" / "plugins"
        dropin.mkdir(parents=True)
        source = dropin / "Example.dll"
        source.write_bytes(b"old")
        manager = ManakaModManager(self.game, self.source, [dropin.parents[1]])
        item = next(item for item in manager.scan() if item["name"] == "Example")
        self.assertTrue(item["userImported"])
        manager.set_enabled(item["id"], True)

        source.write_bytes(b"new")
        manager.scan()
        self.assertEqual(manager.refresh_enabled_from_sources(), 1)
        target = self.game / "BepInEx" / "plugins" / "Example.dll"
        self.assertEqual(target.read_bytes(), b"new")

    @patch("manaka_mod_manager.game_is_running", return_value=False)
    def test_reenable_prefers_new_source_over_old_disabled_copy(self, _running) -> None:
        dropin_root = Path(self.temp.name) / "dropin"
        source = dropin_root / "BepInEx" / "plugins" / "Example.dll"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"old")
        manager = ManakaModManager(self.game, self.source, [dropin_root])
        item = next(item for item in manager.scan() if item["name"] == "Example")
        manager.set_enabled(item["id"], True)
        manager.set_enabled(item["id"], False)

        source.write_bytes(b"new")
        item = next(item for item in manager.scan() if item["name"] == "Example")
        manager.set_enabled(item["id"], True)
        target = self.game / "BepInEx" / "plugins" / "Example.dll"
        self.assertEqual(target.read_bytes(), b"new")
        self.assertFalse(target.with_name("Example.dll.disabled").exists())

    @patch("manaka_mod_manager.game_is_running", return_value=False)
    def test_delete_dropin_removes_repository_and_game_copy(self, _running) -> None:
        dropin_root = Path(self.temp.name) / "dropin"
        source = dropin_root / "BepInEx" / "plugins" / "Example.dll"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"plugin")
        manager = ManakaModManager(self.game, self.source, [dropin_root])
        item = next(item for item in manager.scan() if item["name"] == "Example")
        manager.set_enabled(item["id"], True)
        manager.delete_dropin(item["id"])

        self.assertFalse(source.exists())
        self.assertFalse((self.game / "BepInEx" / "plugins" / "Example.dll").exists())

    @patch("manaka_mod_manager.game_is_running", return_value=False)
    def test_same_name_dropin_replaces_enabled_v2_folder(self, _running) -> None:
        dropin_root = Path(self.temp.name) / "dropin"
        source = dropin_root / "CustomMissions2" / "ExampleV2"
        source.mkdir(parents=True)
        (source / "main.code").write_text("old", encoding="utf-8")
        (source / "stale.code").write_text("stale", encoding="utf-8")
        manager = ManakaModManager(self.game, self.source, [dropin_root])
        item = next(item for item in manager.scan() if item["kind"] == "v2")
        manager.set_enabled(item["id"], True)

        (source / "main.code").write_text("new", encoding="utf-8")
        (source / "stale.code").unlink()
        (source / "added.code").write_text("added", encoding="utf-8")
        manager.scan()
        self.assertEqual(manager.refresh_enabled_from_sources(), 1)

        active = self.game / "CustomMissions2" / "ExampleV2"
        self.assertEqual((active / "main.code").read_text(encoding="utf-8"), "new")
        self.assertTrue((active / "added.code").is_file())
        self.assertFalse((active / "stale.code").exists())


if __name__ == "__main__":
    unittest.main()

