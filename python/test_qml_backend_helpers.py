import unittest
import tempfile
import zipfile
from pathlib import Path

from qml_dashboard_prototype.backend import (
    ControlCenterBackend,
    MOD_SOURCE_LINKS,
    bundled_npc_voice_expected_files,
    bundled_npc_voice_root,
    bundled_npc_subtitle_path,
    bundled_npc_profile_subtitle_path,
    bepinex_runtime_issue,
    build_hud_packet,
    detect_supported_game_version,
    game_build_fingerprint,
    game_unity_version,
    prepare_bundled_unity_base_libraries,
    provision_bepinex_runtime,
    read_npc_profile_subtitle,
    update_bepinex_config,
    validate_supported_game_build,
    uses_bundled_v113_interop,
    windows_network_repair_script,
)
from qml_dashboard_prototype.mod_catalog import USER9527_POST, build_mod_catalog


class V1LocationGuideTests(unittest.TestCase):
    @staticmethod
    def _write_fake_game_build(root: Path, game_bytes: bytes, metadata_bytes: bytes) -> None:
        (root / "GameAssembly.dll").write_bytes(game_bytes)
        metadata = root / "SecretFlasherManaka_Data" / "il2cpp_data" / "Metadata" / "global-metadata.dat"
        metadata.parent.mkdir(parents=True, exist_ok=True)
        metadata.write_bytes(metadata_bytes)

    @staticmethod
    def _write_fake_runtime(root: Path, *, assembly: bytes = b"bundled-v113-interop") -> None:
        (root / "BepInEx" / "core").mkdir(parents=True)
        (root / "BepInEx" / "interop").mkdir(parents=True)
        (root / "BepInEx" / "unity-libs").mkdir(parents=True)
        (root / "BepInEx" / "config").mkdir(parents=True)
        (root / "dotnet").mkdir(parents=True)
        (root / ".doorstop_version").write_text("1", encoding="ascii")
        (root / "doorstop_config.ini").write_text("enabled=true", encoding="ascii")
        (root / "winhttp.dll").write_bytes(b"bootstrap")
        (root / "BEPINEX_LICENSE.txt").write_text("license", encoding="ascii")
        (root / "dotnet" / "runtime.dll").write_bytes(b"runtime")
        (root / "BepInEx" / "core" / "BepInEx.Core.dll").write_bytes(b"new-core")
        (root / "BepInEx" / "interop" / "Assembly-CSharp.dll").write_bytes(assembly)
        (root / "BepInEx" / "interop" / "assembly-hash.txt").write_text("v113", encoding="ascii")
        (root / "BepInEx" / "unity-libs" / "UnityEngine.dll").write_bytes(b"unity")
        (root / "BepInEx" / "config" / "BepInEx.cfg").write_text("[Logging]", encoding="ascii")

    def test_unverified_game_build_is_allowed_for_experimental_testing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "GameAssembly.dll").write_bytes(b"older-game-build")
            metadata = root / "SecretFlasherManaka_Data" / "il2cpp_data" / "Metadata" / "global-metadata.dat"
            metadata.parent.mkdir(parents=True)
            metadata.write_bytes(b"older-metadata")

            allowed, detail = validate_supported_game_build(root)

            self.assertTrue(allowed)
            self.assertIn("未验证版本", detail)

    def test_v112_named_game_folder_is_officially_supported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "SecretFlasherManaka v1.1.2"
            root.mkdir()
            self._write_fake_game_build(root, b"v112-game", b"v112-metadata")

            allowed, detail = validate_supported_game_build(root)

            self.assertTrue(allowed)
            self.assertEqual(detect_supported_game_version(root), "1.1.2")
            self.assertIn("v1.1.2", detail)
            self.assertIn("已支持", detail)
            self.assertFalse(uses_bundled_v113_interop(root))

    def test_incomplete_game_build_is_still_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "GameAssembly.dll").write_bytes(b"partial-game")

            allowed, detail = validate_supported_game_build(root)

            self.assertFalse(allowed)
            self.assertIn("global-metadata.dat", detail)

    def test_game_build_fingerprint_changes_with_il2cpp_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_fake_game_build(root, b"game-a", b"metadata-a")
            first = game_build_fingerprint(root)
            self._write_fake_game_build(root, b"game-b", b"metadata-a")

            self.assertNotEqual(first, game_build_fingerprint(root))

    def test_unknown_build_detects_bundled_v113_interop_as_incompatible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime_source = root / "payload"
            game = root / "game"
            self._write_fake_runtime(runtime_source)
            self._write_fake_runtime(game)

            issue = bepinex_runtime_issue(
                game,
                runtime_source,
                fingerprint="unknown-build",
                verified_build=False,
                manifest={},
            )

            self.assertEqual(issue, "v113-interop-on-unverified-build")

    def test_runtime_repair_preserves_plugins_and_config_and_resets_unknown_interop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime_source = root / "payload"
            game = root / "game"
            self._write_fake_runtime(runtime_source)
            self._write_fake_runtime(game, assembly=b"old-interop")
            plugin = game / "BepInEx" / "plugins" / "ThirdParty" / "Example.dll"
            plugin.parent.mkdir(parents=True)
            plugin.write_bytes(b"plugin")
            user_config = game / "BepInEx" / "config" / "user.cfg"
            user_config.write_text("keep=true", encoding="ascii")

            action, backup = provision_bepinex_runtime(
                game,
                runtime_source,
                verified_build=False,
                repair=True,
            )

            self.assertEqual(action, "repaired")
            self.assertIsNotNone(backup)
            assert backup is not None
            self.assertEqual(plugin.read_bytes(), b"plugin")
            self.assertEqual(user_config.read_text(encoding="ascii"), "keep=true")
            self.assertEqual(
                (backup / "BepInEx" / "interop" / "Assembly-CSharp.dll").read_bytes(),
                b"old-interop",
            )
            self.assertTrue((game / "BepInEx" / "interop").is_dir())
            self.assertFalse((game / "BepInEx" / "interop" / "Assembly-CSharp.dll").exists())
            self.assertEqual((game / "BepInEx" / "core" / "BepInEx.Core.dll").read_bytes(), b"new-core")
            self.assertIn(
                "UpdateInteropAssemblies = true",
                (game / "BepInEx" / "config" / "BepInEx.cfg").read_text(encoding="utf-8"),
            )

    def test_pending_unknown_runtime_enables_interop_generation_without_repair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime_source = root / "payload"
            game = root / "game"
            self._write_fake_runtime(runtime_source)
            self._write_fake_runtime(game, assembly=b"old-interop")
            config = game / "BepInEx" / "config" / "BepInEx.cfg"
            config.write_text(
                "[IL2CPP]\nUpdateInteropAssemblies = false\n\n[Logging]\nUnityLogListening = true\n",
                encoding="utf-8",
            )

            action, backup = provision_bepinex_runtime(
                game,
                runtime_source,
                verified_build=False,
                repair=False,
            )

            self.assertEqual(action, "unchanged")
            self.assertIsNone(backup)
            contents = config.read_text(encoding="utf-8")
            self.assertIn("UpdateInteropAssemblies = true", contents)
            self.assertIn("UnityLogListening = true", contents)

    def test_bundled_unity_libraries_are_cached_for_matching_game_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime_source = root / "payload"
            game = root / "game"
            self._write_fake_runtime(runtime_source)
            self._write_fake_runtime(game)
            (game / "GameAssembly.dll").write_bytes(
                b"prefix\x002022.3.40f1\x00middle\x002022.3.40f1\x00suffix"
            )

            archive = prepare_bundled_unity_base_libraries(game, runtime_source)

            self.assertEqual(game_unity_version(game), "2022.3.40f1")
            self.assertEqual(archive, game / "BepInEx" / "unity-libs" / "2022.3.40.zip")
            assert archive is not None
            with zipfile.ZipFile(archive) as payload:
                self.assertIn("UnityEngine.dll", payload.namelist())

    def test_bundled_npc_subtitles_cover_every_language_and_state(self) -> None:
        for language in ("zh", "ja", "en"):
            for state in ("ambient", "phone", "watching", "alert", "found", "failure", "aftermath"):
                with self.subTest(language=language, state=state):
                    contents = bundled_npc_subtitle_path(language, state).read_text(encoding="utf-8")
                    self.assertTrue(contents.strip())

    def test_profile_subtitles_cover_four_npc_types_in_every_language_and_state(self) -> None:
        for language in ("zh", "ja", "en"):
            source = bundled_npc_profile_subtitle_path(language)
            for profile in ("young_female", "young_male", "older_female", "older_male"):
                for state in ("ambient", "phone", "watching", "alert", "found", "failure", "aftermath"):
                    with self.subTest(language=language, profile=profile, state=state):
                        contents = read_npc_profile_subtitle(source, profile, state)
                        self.assertTrue(contents.strip())

        young_woman = read_npc_profile_subtitle(
            bundled_npc_profile_subtitle_path("zh"), "young_female", "found"
        )
        older_man = read_npc_profile_subtitle(
            bundled_npc_profile_subtitle_path("zh"), "older_male", "found"
        )
        self.assertIn("恶心", young_woman)
        self.assertIn("嘿嘿", older_man)

    def test_npc_subtitle_editor_normalizes_and_limits_user_text(self) -> None:
        normalized = ControlCenterBackend._normalize_npc_subtitle_text("  第一行  \r\n\r\n# 注释\r\n第二行 ")

        self.assertEqual(normalized, "第一行\n第二行\n")
        with self.assertRaises(ValueError):
            ControlCenterBackend._normalize_npc_subtitle_text("\n# only a comment\n")

    def test_aftermath_editor_preserves_paragraph_boundaries(self) -> None:
        normalized = ControlCenterBackend._normalize_npc_subtitle_text(
            "  第一段第一行  \r\n第一段第二行\r\n\r\n\r\n# 注释\r\n第二段",
            "aftermath",
        )

        self.assertEqual(normalized, "第一段第一行\n第一段第二行\n\n第二段\n")

    def test_npc_voice_payload_contains_only_japanese_runtime_wavs(self) -> None:
        mappings = bundled_npc_voice_expected_files(bundled_npc_voice_root())

        self.assertEqual(len(mappings), 90)
        self.assertTrue(all(source.is_file() for source, _relative in mappings))
        self.assertTrue(all(relative.suffix == ".wav" for _source, relative in mappings))
        self.assertTrue(all(relative.parts[0] == "ja" for _source, relative in mappings))

    def test_bepinex_config_update_preserves_unrelated_settings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "local.manaka.npcvoices.cfg"
            path.write_text(
                "[General]\nLanguage = zh\nVoiceEnabled = true\n\n[Audio]\nVolume = 0.42\n",
                encoding="utf-8",
            )

            update_bepinex_config(
                path,
                {
                    ("General", "Language"): "ja",
                    ("General", "SubtitlesEnabled"): "false",
                },
            )
            contents = path.read_text(encoding="utf-8")

            self.assertIn("Language = ja", contents)
            self.assertIn("SubtitlesEnabled = false", contents)
            self.assertIn("Volume = 0.42", contents)

    def test_hud_packet_clamps_values_and_keeps_a_stable_shape(self) -> None:
        packet = build_hud_packet(
            12,
            visible=True,
            connected=True,
            active=True,
            strength_a=123,
            strength_b=-4,
            pulse_a=1.8,
            pulse_b=-0.1,
        )

        self.assertEqual(
            packet.decode("ascii"),
            "MANAKA_HUD_V1|12|1|1|1|100.00|0.00|1.000|0.000|END",
        )

    def test_repair_script_targets_selected_adapter_and_private_firewall_port(self) -> None:
        script = windows_network_repair_script("192.168.50.12", 9999)

        self.assertIn("$targetIp = '192.168.50.12'", script)
        self.assertIn("ManakaDGLab-TCP-9999", script)
        self.assertIn("-LocalPort $port -Profile Private", script)
        self.assertIn("Set-NetConnectionProfile -InterfaceIndex", script)

    def test_repair_script_rejects_non_lan_address(self) -> None:
        with self.assertRaises(ValueError):
            windows_network_repair_script("127.0.0.1", 9999)

    def test_external_author_links_are_https_and_allowlisted(self) -> None:
        allowed = [
            "https://www.dlsite.com/maniax/work/=/product_id/RJ01389782.html",
            "https://f95zone.to/threads/example",
            "https://github.com/PeanutsZheng/ModManager/releases",
            "https://mega.nz/folder/example",
            "https://t.me/example",
        ]
        for value in allowed:
            with self.subTest(value=value):
                self.assertTrue(ControlCenterBackend._is_allowed_external_url(value))

        blocked = [
            "http://f95zone.to/threads/example",
            "https://f95zone.to.evil.example/threads/example",
            "file:///C:/Windows/System32/cmd.exe",
            "javascript:alert(1)",
        ]
        for value in blocked:
            with self.subTest(value=value):
                self.assertFalse(ControlCenterBackend._is_allowed_external_url(value))

        self.assertTrue(MOD_SOURCE_LINKS)
        self.assertTrue(
            all(ControlCenterBackend._is_allowed_external_url(item["url"]) for item in MOD_SOURCE_LINKS)
        )

    def test_bilingual_catalog_is_complete_and_pinned(self) -> None:
        chinese = build_mod_catalog("zh")
        english = build_mod_catalog("en")

        self.assertEqual(len(chinese), 133)
        self.assertEqual(len(english), 133)
        self.assertEqual([item["category"] for item in chinese[:2]], ["core", "core"])
        self.assertTrue(all(item["pinned"] for item in chinese[:2]))
        self.assertIn("任务加载器", chinese[0]["displayName"])
        self.assertIn("V1 Loader", english[0]["displayName"])
        self.assertTrue(
            all(ControlCenterBackend._is_allowed_external_url(item["url"]) for item in chinese)
        )

    def test_user9527_uses_the_exact_post_link(self) -> None:
        matches = [item for item in build_mod_catalog("zh") if item["reference"] == "#978"]

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["url"], USER9527_POST)

    def test_current_enabled_inventory_is_a_file_state_filter(self) -> None:
        inventory = [
            {"id": "plugin|Enabled.dll", "enabled": True, "name": "Enabled"},
            {"id": "plugin|Disabled.dll", "enabled": False, "name": "Disabled"},
            {"id": "v2|Installed", "enabled": True, "name": "Installed"},
        ]

        current = ControlCenterBackend._enabled_mods(inventory)

        self.assertEqual([item["name"] for item in current], ["Enabled", "Installed"])
        self.assertIsNot(current[0], inventory[0])

    def test_current_loaded_snapshot_retains_disabled_cards_until_rescan(self) -> None:
        inventory = [
            {"id": "plugin|Enabled.dll", "enabled": True, "name": "Enabled"},
            {"id": "plugin|JustDisabled.dll", "enabled": False, "name": "Just disabled"},
            {"id": "plugin|PreviouslyDisabled.dll", "enabled": False, "name": "Old"},
        ]

        current = ControlCenterBackend._loaded_mods(
            inventory,
            ("plugin|Enabled.dll", "plugin|JustDisabled.dll"),
        )

        self.assertEqual([item["name"] for item in current], ["Enabled", "Just disabled"])
        self.assertFalse(current[0]["sessionDisabled"])
        self.assertTrue(current[1]["sessionDisabled"])

    def test_location_guide_is_attached_to_v1_mod_cards(self) -> None:
        inventory = [
            {"kind": "v1", "name": "Apart"},
            {"kind": "v1", "name": "Unknown third-party mission"},
            {"kind": "plugin", "name": "SFM_custom_mission"},
        ]

        ControlCenterBackend._annotate_v1_locations(inventory)

        self.assertTrue(inventory[0]["hasLocationGuide"])
        self.assertIn("院子", inventory[0]["location"])
        self.assertIn("家门口正对面", inventory[0]["location"])
        self.assertFalse(inventory[1]["hasLocationGuide"])
        self.assertFalse(inventory[2]["hasLocationGuide"])


if __name__ == "__main__":
    unittest.main()
