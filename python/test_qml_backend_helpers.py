import unittest

from qml_dashboard_prototype.backend import ControlCenterBackend


class V1LocationGuideTests(unittest.TestCase):
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
