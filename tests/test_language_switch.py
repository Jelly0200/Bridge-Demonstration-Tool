import unittest
from unittest.mock import patch

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtWidgets import QApplication, QLabel, QMessageBox, QTreeWidgetItem

from src.ui.main_window import MainWindow
from src.ui.i18n import translate_text


class TestLanguageSwitch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_toolbar_switch_translates_interface_and_keeps_dds_in_english(self):
        window = MainWindow()
        self.addCleanup(window.close)

        self.assertGreaterEqual(window.width(), 1600)
        self.assertGreaterEqual(window.height(), 1000)
        with patch(
            "src.ui.main_window.QInputDialog.getItem",
            return_value=("中文", True),
        ):
            window.btn_language.click()

        self.assertEqual(window.language, "zh")
        self.assertEqual(window.btn_language.text(), "English")
        self.assertEqual(window.btn_test_mode.text(), "练习构建")
        self.assertEqual(window.btn_add_asset.text(), "添加")
        self.assertEqual(window.toolbar.windowTitle(), "控制工具栏")
        self.assertEqual(window.btn_language.toolTip(), "切换中英文。")
        self.assertEqual(
            window.table_view.btn_dds_display.toolTip(),
            "切换显示当前方赢墩数或定约所需墩数差。",
        )
        self.assertEqual(window.tree_view.headerItem().text(0), "资源树（文件夹 / 牌例 / 牌局 / 场景）")
        self.assertEqual(window.table_view.btn_settings.text(), "设置")
        self.assertEqual(window.table_view.btn_dds_display.text(), "DDS: Tricks")

        window.statusBar().showMessage("Test construction selected")
        self.assertEqual(window.statusBar().currentMessage(), "已选择练习构建模式")

        with patch(
            "src.ui.main_window.QInputDialog.getItem",
            return_value=("English", True),
        ):
            window.btn_language.click()

        self.assertEqual(window.language, "en")
        self.assertEqual(window.btn_language.text(), "中文")
        self.assertEqual(window.btn_test_mode.text(), "Test construction")
        self.assertEqual(window.table_view.btn_settings.text(), "Settings")

    def test_cascade_menus_are_installed_and_translated(self):
        window = MainWindow()
        self.addCleanup(window.close)

        self.assertFalse(window.menuBar().isNativeMenuBar())
        self.assertFalse(window.menuBar().isHidden())
        self.assertGreaterEqual(window.menuBar().minimumHeight(), 40)
        self.assertIn("#111827", window.menuBar().styleSheet())
        self.assertTrue(window.toolbar.isHidden())
        self.assertEqual(
            [action.text() for action in window.menuBar().actions()],
            ["Administrator", "Tool", "Test", "Explorer"],
        )
        with patch(
            "src.ui.main_window.QInputDialog.getItem",
            return_value=("中文", True),
        ):
            window.btn_language.click()
        self.assertEqual(
            [action.text() for action in window.menuBar().actions()],
            ["管理员", "工具", "测试", "资源管理器"],
        )

    def test_language_menu_opens_a_choice_dialog_before_switching(self):
        window = MainWindow()
        self.addCleanup(window.close)

        with patch(
            "src.ui.main_window.QInputDialog.getItem",
            return_value=("中文", False),
        ) as choose:
            window.choose_language()
        choose.assert_called_once()
        self.assertEqual(window.language, "en")

        with patch(
            "src.ui.main_window.QInputDialog.getItem",
            return_value=("中文", True),
        ):
            window.choose_language()
        self.assertEqual(window.language, "zh")

    def test_tool_and_explorer_menus_open_reference_tools_not_asset_actions(self):
        window = MainWindow()
        self.addCleanup(window.close)

        admin_actions = [
            action.text()
            for action in window.administration_menu.actions()
            if not action.isSeparator()
        ]
        self.assertEqual(
            admin_actions,
            [
                "Administration Registration",
                "Administration Login",
                "Administration Logout",
                "Student login",
                "Export administrator data",
                "Import administrator data",
                "Administration Lockdown",
            ],
        )
        self.assertEqual(
            [action.text() for action in window.tool_menu.actions()],
            [
                "Monitor",
                "Instruction",
                "Language",
                "Keyboard shortcuts",
            ],
        )
        self.assertEqual(
            [action.text() for action in window.test_menu.actions()],
            [
                "Test construction",
                "Run Test",
                "Examine test results",
                "Generate test report",
                "Student management",
            ],
        )
        self.assertEqual(
            [action.text() for action in window.explorer_menu.actions()],
            ["README.md", "requirements.txt"],
        )
        with patch("src.ui.main_window.KeyboardShortcutsDialog") as dialog_class:
            window.show_keyboard_shortcuts()
        dialog_class.assert_called_once_with("en", window)
        dialog_class.return_value.exec.assert_called_once()

        with patch("src.ui.main_window.ProjectDocumentDialog") as document_class:
            window.show_project_document("README.md")
        self.assertIn("Bridge Demonstration Tool", document_class.call_args.args[1])
        document_class.return_value.exec.assert_called_once()
        window.set_language("zh")
        self.assertIn(
            "生成测试报告",
            [action.text() for action in window.test_menu.actions()],
        )

    def test_content_transfer_actions_require_an_administrator(self):
        window = MainWindow()
        self.addCleanup(window.close)

        self.assertFalse(window.action_export_admin_data.isEnabled())
        self.assertFalse(window.action_import_admin_data.isEnabled())
        window.set_language("zh")
        self.assertEqual(window.action_export_admin_data.text(), "导出管理员数据")
        self.assertEqual(window.action_import_admin_data.text(), "导入管理员数据")
        with patch.object(window, "_first_case_id", return_value=None):
            with patch.object(window.tree_view, "load_tree_data"):
                window._activate_admin(37, "transfer_admin")
        self.assertTrue(window.action_export_admin_data.isEnabled())
        self.assertTrue(window.action_import_admin_data.isEnabled())

    def test_export_prompts_twice_and_saves_encrypted_package(self):
        window = MainWindow()
        self.addCleanup(window.close)
        window.active_admin_id = 55
        export_path = "/tmp/bridge-workspace"
        with (
            patch(
                "src.ui.main_window.QFileDialog.getSaveFileName",
                return_value=(export_path, ""),
            ),
            patch(
                "src.ui.main_window.QInputDialog.getText",
                side_effect=[
                    ("a strong portable passphrase", True),
                    ("a strong portable passphrase", True),
                ],
            ),
            patch("src.ui.main_window.ContentTransferService") as service_class,
            patch("src.ui.main_window.show_message"),
        ):
            window.export_admin_data()

        service_class.assert_called_once_with(window.repo.db)
        service_class.return_value.export_admin_data.assert_called_once_with(
            55,
            f"{export_path}.bdtpack",
            "a strong portable passphrase",
        )

    def test_import_verifies_and_confirms_before_adding_package(self):
        window = MainWindow()
        self.addCleanup(window.close)
        window.active_admin_id = 56
        window.active_admin_name = "receiver"
        payload = {
            "source_administrator": "sender",
            "tables": {"Folder": [{"Id": 1}], "Test": [{"Id": 1}]},
        }
        with (
            patch(
                "src.ui.main_window.QFileDialog.getOpenFileName",
                return_value=("/tmp/workspace.bdtpack", ""),
            ),
            patch(
                "src.ui.main_window.QInputDialog.getText",
                return_value=("a strong portable passphrase", True),
            ),
            patch("src.ui.main_window.ContentTransferService") as service_class,
            patch(
                "src.ui.main_window.show_message",
                side_effect=[
                    None,
                    QMessageBox.StandardButton.Yes,
                    None,
                ],
            ),
            patch.object(window, "_refresh_assets") as refresh_assets,
        ):
            service_class.return_value.read_package.return_value = payload
            window.import_admin_data()

        service_class.return_value.read_package.assert_called_once_with(
            "/tmp/workspace.bdtpack",
            "a strong portable passphrase",
        )
        service_class.return_value.import_admin_data.assert_called_once_with(
            56,
            payload,
        )
        refresh_assets.assert_called_once()

    def test_explorer_actions_localize_and_reuse_chinese_readme(self):
        window = MainWindow()
        self.addCleanup(window.close)

        window.set_language("zh")
        self.assertEqual(
            [action.text() for action in window.explorer_menu.actions()],
            ["项目说明（README.md）", "依赖清单（requirements.txt）"],
        )
        self.assertEqual(len(window.explorer_menu.actions()), 2)

        with patch("src.ui.main_window.ProjectDocumentDialog") as document_class:
            window.show_project_document("README.md")

        title, contents = document_class.call_args.args[:2]
        self.assertEqual(title, "项目说明（README.md）")
        self.assertIn("# 桥牌演示工具", contents)
        document_class.return_value.exec.assert_called_once()

        window.set_language("en")
        self.assertEqual(
            [action.text() for action in window.explorer_menu.actions()],
            ["README.md", "requirements.txt"],
        )

    def test_translation_replacement_does_not_corrupt_english_compounds(self):
        self.assertEqual(
            translate_text("Control Toolbar", "zh"),
            "控制工具栏",
        )
        self.assertEqual(translate_text("Toolbar", "zh"), "Toolbar")

    def test_checkable_controls_have_readable_indicators(self):
        window = MainWindow()
        self.addCleanup(window.close)

        stylesheet = window.styleSheet()
        self.assertIn("QCheckBox::indicator", stylesheet)
        self.assertIn("QListView::indicator", stylesheet)
        self.assertIn("width: 20px;", stylesheet)

    def test_language_switch_after_admin_activation(self):
        window = MainWindow()
        self.addCleanup(window.close)
        with (
            patch.object(window, "_first_case_id", return_value=None),
            patch("src.ui.views.tree_view.TreeView.load_tree_data"),
        ):
            window._activate_admin(12, "teacher")
            window.tree_view.clear()
            asset_item = QTreeWidgetItem(window.tree_view, ["Lessons"])
            asset_item.setData(
                0,
                Qt.ItemDataRole.UserRole,
                ("folder", 12),
            )
            with patch(
                "src.ui.main_window.QInputDialog.getItem",
                return_value=("中文", True),
            ):
                window.btn_language.click()

        self.assertEqual(window.language, "zh")
        self.assertEqual(window.btn_add_asset.text(), "添加")
        self.assertEqual(window.tree_view.topLevelItem(0).text(0), "Lessons")

    def test_language_switch_ignores_deleted_qt_objects(self):
        window = MainWindow()
        self.addCleanup(window.close)
        temporary_label = QLabel("Temporary", window)
        window.language_controller.install(temporary_label)

        temporary_label.deleteLater()
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        window.language_controller.set_language("zh")

        self.assertEqual(window.btn_test_mode.text(), "练习构建")

    def test_dynamic_login_welcome_message_translates(self):
        message = "Welcome back, administrator [teacher]!\nAdvanced access is active."

        self.assertEqual(
            translate_text(message, "zh"),
            "欢迎回来，管理员 [teacher]！\n高级权限已激活。",
        )
