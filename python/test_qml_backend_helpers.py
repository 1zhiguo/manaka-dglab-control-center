import unittest

from qml_dashboard_prototype.backend import (
    ControlCenterBackend,
    MOD_SOURCE_LINKS,
    build_hud_packet,
    windows_network_repair_script,
)
from qml_dashboard_prototype.mod_catalog import USER9527_POST, build_mod_catalog


class V1LocationGuideTests(unittest.TestCase):
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
