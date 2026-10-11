import tempfile
import unittest
import zipfile
from pathlib import Path

from manaka_dropin_importer import DropInModImporter
from manaka_mod_manager import ManakaModManager


class DropInImporterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        base = Path(self.temp.name)
        self.dropin = base / "dropin_mods"
        self.importer = DropInModImporter(self.dropin)
        self.importer.ensure_layout()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_imports_loose_dll_json_and_v2_folder(self) -> None:
        (self.importer.incoming / "Example.dll").write_bytes(b"dll")
        (self.importer.incoming / "Mission.json").write_text("{}", encoding="utf-8")
        v2 = self.importer.incoming / "MyV2"
        v2.mkdir()
        (v2 / "main.code").write_text("code", encoding="utf-8")

        result = self.importer.import_all()
        self.assertEqual((result["plugins"], result["v1"], result["v2"]), (1, 1, 1))
        self.assertTrue((self.importer.plugins / "Example.dll").is_file())
        self.assertTrue((self.importer.v1 / "Mission.json").is_file())
        self.assertTrue((self.importer.v2 / "MyV2" / "main.code").is_file())
        self.assertEqual(list(self.importer.incoming.iterdir()), [])
        self.assertTrue((self.importer.archive / "Example.dll").is_file())

    def test_imports_wrapped_zip_layout(self) -> None:
        archive = self.importer.incoming / "pack.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("Pack/BepInEx/plugins/ZipPlugin.dll", b"dll")
            bundle.writestr("Pack/CustomMissions1/ZipMission.json", "{}")
            bundle.writestr("Pack/CustomMissions2/ZipV2/main.code", "code")
        result = self.importer.import_all()
        self.assertEqual((result["plugins"], result["v1"], result["v2"]), (1, 1, 1))

    def test_rejects_zip_path_traversal(self) -> None:
        archive = self.importer.incoming / "unsafe.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("../outside.dll", b"bad")
        result = self.importer.import_all()
        self.assertEqual(len(result["errors"]), 1)
        self.assertFalse((self.dropin.parent / "outside.dll").exists())

    def test_manager_merges_dropin_repository_and_prefers_it(self) -> None:
        base = Path(self.temp.name)
        game = base / "game"
        bundled = base / "bundled"
        game.mkdir()
        (game / "SecretFlasherManaka.exe").write_bytes(b"game")
        builtin_plugin = bundled / "plugins" / "files" / "Example.dll"
        builtin_plugin.parent.mkdir(parents=True)
        builtin_plugin.write_bytes(b"builtin")
        (self.importer.incoming / "Example.dll").write_bytes(b"dropin")
        self.importer.import_all()

        manager = ManakaModManager(game, bundled, [self.importer.repository])
        manager.scan()
        entry = next(value for value in manager.entries.values() if value.name == "Example")
        self.assertEqual(Path(entry.source).read_bytes(), b"dropin")

    def test_same_name_folder_import_replaces_instead_of_merging(self) -> None:
        package = self.importer.incoming / "MyV2"
        package.mkdir()
        (package / "main.code").write_text("old", encoding="utf-8")
        (package / "removed.code").write_text("stale", encoding="utf-8")
        self.importer.import_all()

        package = self.importer.incoming / "MyV2"
        package.mkdir()
        (package / "main.code").write_text("new", encoding="utf-8")
        (package / "added.code").write_text("added", encoding="utf-8")
        self.importer.import_all()

        imported = self.importer.v2 / "MyV2"
        self.assertEqual((imported / "main.code").read_text(encoding="utf-8"), "new")
        self.assertTrue((imported / "added.code").is_file())
        self.assertFalse((imported / "removed.code").exists())


if __name__ == "__main__":
    unittest.main()

