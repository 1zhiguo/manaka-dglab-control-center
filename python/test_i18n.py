import unittest

from qml_dashboard_prototype.i18n import translate


class RuntimeTranslationTests(unittest.TestCase):
    def test_core_navigation_has_english_translation(self) -> None:
        self.assertEqual(translate("实时仪表盘", "en"), "Dashboard")
        self.assertEqual(translate("Mod 管理器", "en"), "Mod Manager")

    def test_chinese_mode_preserves_source_copy(self) -> None:
        self.assertEqual(translate("暂停输出", "zh"), "暂停输出")

    def test_unknown_third_party_metadata_is_preserved(self) -> None:
        self.assertEqual(translate("Unknown Mission by Author", "en"), "Unknown Mission by Author")


if __name__ == "__main__":
    unittest.main()
