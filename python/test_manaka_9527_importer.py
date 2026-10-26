import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from manaka_9527_importer import Pack9527Error, Pack9527Importer
from manaka_mod_manager import ManakaModManager


class Pack9527ImporterTests(unittest.TestCase):
    TEST_ROOT = Path(__file__).resolve().parent

    def make_pack(self, root: Path) -> Path:
        pack = root / "download" / "SecretFlasherManaka 9527 collection"
        plugins = pack / "BepInEx" / "plugins"
        (plugins / "Extras").mkdir(parents=True)
        (plugins / "SFM_custom_mission.dll").write_bytes(b"v1-loader")
        (plugins / "SFM_custom_mission_v2.dll").write_bytes(b"v2-loader")
        (plugins / "Extras" / "Optional.dll").write_bytes(b"optional")
        (plugins / "Extras" / "data.bin").write_bytes(b"resource")
        config = pack / "BepInEx" / "config"
        config.mkdir(parents=True)
        (config / "optional.cfg").write_text("enabled=true", encoding="utf-8")
        v1 = pack / "CustomMissions" / "admirer"
        v1.mkdir(parents=True)
        (v1 / "admirer_main.json").write_text("{}", encoding="utf-8")
        v2 = pack / "CustomMissions2" / "ExampleV2"
        v2.mkdir(parents=True)
        (v2 / "meta.json").write_text(json.dumps({"title": "Example"}), encoding="utf-8")
        (pack / "必读安装说明.txt").write_text("read me", encoding="utf-8")
        return pack

    def make_game(self, root: Path) -> Path:
        game = root / "game"
        (game / "BepInEx" / "core").mkdir(parents=True)
        (game / "BepInEx" / "plugins" / "ManakaDGLabTelemetry").mkdir(parents=True)
        (game / "SecretFlasherManaka.exe").write_bytes(b"")
        (game / "BepInEx" / "core" / "BepInEx.Core.dll").write_bytes(b"core")
        (game / "BepInEx" / "plugins" / "ManakaDGLabTelemetry" / "ManakaDGLabTelemetry.dll").write_bytes(b"telemetry")
        return game

    def test_inspect_accepts_parent_of_single_extracted_pack(self) -> None:
        with tempfile.TemporaryDirectory(dir=self.TEST_ROOT) as temp:
            base = Path(temp)
            pack = self.make_pack(base)

            result = Pack9527Importer().inspect(pack.parent)

            self.assertEqual(Path(result.root), pack)
            self.assertEqual(result.plugins, 3)
            self.assertEqual(result.v1_missions, 1)
            self.assertEqual(result.v2_packages, 1)
            self.assertTrue(result.ready)
            self.assertIn("必读安装说明.txt", result.readmes)

    @patch("manaka_9527_importer.game_is_running", return_value=False)
    def test_install_keeps_only_two_loaders_active_and_backs_up_overwrites(self, _running) -> None:
        with tempfile.TemporaryDirectory(dir=self.TEST_ROOT) as temp:
            base = Path(temp)
            pack = self.make_pack(base)
            game = self.make_game(base)
            existing = game / "BepInEx" / "plugins" / "Extras" / "Optional.dll"
            existing.parent.mkdir(parents=True)
            existing.write_bytes(b"old")

            result = Pack9527Importer().install(pack, game)

            self.assertTrue((game / "BepInEx" / "plugins" / "SFM_custom_mission.dll").is_file())
            self.assertTrue((game / "BepInEx" / "plugins" / "SFM_custom_mission_v2.dll").is_file())
            self.assertFalse(existing.exists())
            self.assertEqual(existing.with_name("Optional.dll.disabled").read_bytes(), b"optional")
            self.assertTrue((game / "BepInEx" / "plugins" / "ManakaDGLabTelemetry" / "ManakaDGLabTelemetry.dll").is_file())
            self.assertFalse((game / "CustomMissions" / "admirer" / "admirer_main.json").exists())
            self.assertTrue((game / "ManakaModManager" / "disabled" / "v1" / "admirer" / "admirer_main.json").is_file())
            self.assertFalse((game / "CustomMissions2" / "ExampleV2").exists())
            self.assertTrue((game / "ManakaModManager" / "disabled" / "v2" / "ExampleV2" / "meta.json").is_file())
            self.assertEqual(result["enabled_plugins"], 2)
            self.assertEqual(result["disabled_plugins"], 1)
            backup = Path(result["backup"])
            self.assertEqual(
                (backup / "files" / "BepInEx" / "plugins" / "Extras" / "Optional.dll").read_bytes(),
                b"old",
            )

            inventory = ManakaModManager(game, pack).scan()
            entries = {item["id"]: item for item in inventory}
            self.assertTrue(entries["plugin|SFM_custom_mission.dll"]["enabled"])
            self.assertTrue(entries["plugin|SFM_custom_mission_v2.dll"]["enabled"])
            self.assertFalse(entries["v1|admirer"]["enabled"])
            self.assertFalse(entries["v2|ExampleV2"]["enabled"])

    def test_rejects_incomplete_pack(self) -> None:
        with tempfile.TemporaryDirectory(dir=self.TEST_ROOT) as temp:
            folder = Path(temp)
            (folder / "BepInEx" / "plugins").mkdir(parents=True)
            with self.assertRaises(Pack9527Error):
                Pack9527Importer().inspect(folder)

    def test_rejects_same_directory_before_touching_any_files(self) -> None:
        with tempfile.TemporaryDirectory(dir=self.TEST_ROOT) as temp:
            pack = self.make_pack(Path(temp))
            before = {p.relative_to(pack): p.read_bytes() for p in pack.rglob("*") if p.is_file()}
            with self.assertRaisesRegex(Pack9527Error, "不能相同或互相包含"):
                Pack9527Importer().install(pack, pack)
            after = {p.relative_to(pack): p.read_bytes() for p in pack.rglob("*") if p.is_file()}
            self.assertEqual(after, before)
            self.assertFalse((pack / "ManakaModManager").exists())

    def test_rejects_target_inside_source_before_creating_backups(self) -> None:
        with tempfile.TemporaryDirectory(dir=self.TEST_ROOT) as temp:
            pack = self.make_pack(Path(temp))
            game = self.make_game(pack)
            before = {p.relative_to(pack): p.read_bytes() for p in pack.rglob("*") if p.is_file()}
            with self.assertRaisesRegex(Pack9527Error, "不能相同或互相包含"):
                Pack9527Importer().install(pack, game)
            self.assertEqual(before, {p.relative_to(pack): p.read_bytes() for p in pack.rglob("*") if p.is_file()})
            self.assertFalse((game / "ManakaModManager").exists())

    def test_rejects_source_inside_target_before_creating_backups(self) -> None:
        with tempfile.TemporaryDirectory(dir=self.TEST_ROOT) as temp:
            game = self.make_game(Path(temp))
            pack = self.make_pack(game)
            before = {p.relative_to(game): p.read_bytes() for p in game.rglob("*") if p.is_file()}
            with self.assertRaisesRegex(Pack9527Error, "不能相同或互相包含"):
                Pack9527Importer().install(pack, game)
            self.assertEqual(before, {p.relative_to(game): p.read_bytes() for p in game.rglob("*") if p.is_file()})
            self.assertFalse((game / "ManakaModManager").exists())


if __name__ == "__main__":
    unittest.main()
