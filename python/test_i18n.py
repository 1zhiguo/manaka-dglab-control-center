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

    def test_fixed_width_controls_use_compact_english_labels(self) -> None:
        expected = {
            "存档工具": "Save",
            "保存波形策略": "Save",
            "玩法与限制": "Gameplay",
            "外观与音效": "Media",
            "工具与辅助": "Tools",
            "打开原帖页": "Link",
            "导入并扫描": "Import",
            "我已阅读并同意": "Agree",
        }

        for source, concise_label in expected.items():
            with self.subTest(source=source):
                self.assertEqual(translate(source, "en"), concise_label)

    def test_user9527_import_steps_are_bilingual(self) -> None:
        expected = {
            "下载整合包": "Download",
            "完整解压": "Extract",
            "启动导入向导": "Import",
            "开始导入 9527 汉化整合": "Start Import",
        }

        for source, english in expected.items():
            with self.subTest(source=source):
                self.assertEqual(translate(source, "en"), english)

    def test_action_mapping_and_wave_editor_are_bilingual(self) -> None:
        expected = {
            "官方波形": "Official",
            "自定义波形": "Custom Wave",
            "动作映射": "Action Map",
            "规律动作": "Rhythmic",
            "静态姿势": "Static Pose",
            "普通交互": "Interaction",
            "自定义波形编辑器": "Custom Wave Editor",
            "我的波形": "My Wave",
            "恢复推荐": "Reset",
            "通道策略": "Channel Mapping",
            "A 通道 · 心率": "Channel A · Heart Rate",
            "B 通道 · 动作": "Channel B · Actions",
            "无输出": "No output",
        }

        for source, english in expected.items():
            with self.subTest(source=source):
                self.assertEqual(translate(source, "en"), english)


if __name__ == "__main__":
    unittest.main()
