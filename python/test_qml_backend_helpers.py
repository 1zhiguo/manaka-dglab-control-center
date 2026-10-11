import unittest

from qml_dashboard_prototype.backend import ControlCenterBackend


class V1LocationGuideTests(unittest.TestCase):
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
