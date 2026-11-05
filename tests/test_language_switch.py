import unittest
from unittest.mock import patch

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QMessageBox,
    QSlider,
    QTreeWidgetItem,
)

from src.ui.main_window import MainWindow
from src.ui.i18n import translate_text
from src.security.passwords import hash_password
from src.ui.dialogs.export_selection_dialog import ExportSelectionDialog
from src.ui.widgets.hand_widget import CardWidget


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
        self.assertEqual(
            window.table_view.robot_card_sound_action.text(),
            "播放出牌音效",
        )
        self.assertEqual(window.language, "zh")
        self.assertEqual(window.btn_language.text(), "English")
        self.assertEqual(window.btn_test_mode.text(), "练习构建")
        self.assertEqual(window.btn_add_asset.text(), "添加")
        self.assertEqual(window.toolbar.windowTitle(), "控制工具栏")
        self.assertEqual(window.btn_language.toolTip(), "切换中英文。")
        self.assertEqual(window.tree_view.headerItem().text(0), "资源树（文件夹 / 牌例 / 牌局 / 场景）")
        self.assertEqual(window.table_view.btn_bidding.text(), "叫牌")
        self.assertEqual(
            window.font_color_action.text(),
            "应用字体颜色...",
        )
        self.assertEqual(
            window.table_view.dds_visibility_action.text(),
            "Show DDS matrix",
        )

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
        self.assertEqual(window.table_view.btn_bidding.text(), "Bidding")

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
            ["Administrator", "Preference", "Tool", "Test", "Explorer"],
        )
        self.assertEqual(
            [action.text() for action in window.preference_menu.actions()],
            ["DDS", "Styles", "Robot", "Sound", "View"],
        )
        preference_submenus = {
            action.text(): action.menu()
            for action in window.preference_menu.actions()
        }
        explorer_submenus = {
            action.text(): action.menu()
            for action in window.explorer_menu.actions()
            if action.menu() is not None
        }
        self.assertEqual(
            [action.text() for action in preference_submenus["DDS"].actions()
             if not action.isSeparator()],
            ["Show DDS matrix", "Tricks", "Contract tricks"],
        )
        self.assertEqual(
            [
                action.text()
                for action in explorer_submenus["Labels"].actions()
            ],
            ["Show label definition"],
        )
        styles_actions = [
            action
            for action in preference_submenus["Styles"].actions()
            if not action.isSeparator()
        ]
        self.assertEqual(len(styles_actions), 11)
        self.assertIsInstance(styles_actions[0].defaultWidget().findChild(QSlider), QSlider)
        self.assertEqual(
            styles_actions[1].defaultWidget().findChild(QSlider),
            window.table_view.suit_symbol_size_slider,
        )
        self.assertEqual(
            styles_actions[2].defaultWidget().findChild(QSlider),
            window.table_view.font_size_slider,
        )
        self.assertFalse(window.table_view.font_size_slider.hasTracking())
        self.assertEqual(
            styles_actions[3].text(),
            "Application font color...",
        )
        self.assertEqual(
            styles_actions[4].text(),
            "Application background color...",
        )
        self.assertIs(
            styles_actions[5].defaultWidget().findChild(QSlider),
            window.asset_tree_width_slider,
        )
        self.assertIs(
            styles_actions[6].defaultWidget().findChild(QSlider),
            window.upper_panel_height_slider,
        )
        self.assertIs(
            styles_actions[7].defaultWidget().findChild(QSlider),
            window.central_panel_height_slider,
        )
        self.assertEqual(
            [action.text() for action in styles_actions[8:]],
            [
                "Asset tree color...",
                "Upper panel color...",
                "Central panel color...",
            ],
        )
        previous_font = QApplication.font()
        self.addCleanup(QApplication.setFont, previous_font)
        menu_bar_maximum_height = window.menuBar().maximumHeight()
        card = CardWidget(
            "SA",
            parent=window.table_view.hand_widgets["SOUTH"],
        )
        card_font_size = card.rank_label.font().pixelSize()
        window.table_view.font_size_slider.setValue(19)
        QApplication.processEvents()
        window.table_view.set_application_font_color("#123456")
        window.table_view.set_application_background_color("#123123")
        self.assertEqual(QApplication.font().pixelSize(), 19)
        self.assertEqual(window.btn_login.font().pixelSize(), 19)
        self.assertEqual(window.tree_view.font().pixelSize(), 19)
        self.assertEqual(window.btn_add_asset.font().pixelSize(), 19)
        self.assertEqual(window.table_view.btn_bidding.font().pixelSize(), 19)
        self.assertEqual(window.table_view.center_info.font().pixelSize(), 19)
        self.assertEqual(window.table_view.dds_result_table.font().pixelSize(), 19)
        self.assertEqual(card.rank_label.font().pixelSize(), card_font_size)
        self.assertNotIn("font-size: 19px;", window.styleSheet())
        self.assertIn("color: #123456;", window.styleSheet())
        self.assertIn("background-color: #123123;", window.styleSheet())
        self.assertIn("font-size: 19px;", window.menuBar().styleSheet())

        window.asset_tree_width_slider.setValue(420)
        window.upper_panel_height_slider.setValue(52)
        window.central_panel_height_slider.setValue(720)
        QApplication.processEvents()
        self.assertEqual(window.panel_styles["asset_tree_width_px"], 420)
        self.assertEqual(window.panel_styles["upper_panel_height_px"], 52)
        self.assertEqual(window.panel_styles["central_panel_height_px"], 720)
        self.assertEqual(window.table_view.top_bar_widget.height(), 52)
        self.assertEqual(
            window.menuBar().maximumHeight(),
            menu_bar_maximum_height,
        )
        self.assertGreaterEqual(window.table_view.minimumHeight(), 720)
        with patch(
            "src.ui.main_window.QColorDialog.getColor",
            return_value=QColor("#123456"),
        ):
            window._choose_panel_color(
                "central_panel_color",
                "Central panel color...",
            )
        self.assertIn("background-color: #123456;", window.styleSheet())
        view_actions = [
            action
            for action in preference_submenus["View"].actions()
            if not action.isSeparator()
        ]
        self.assertEqual(view_actions[-1].text(), "Rotate view")
        robot_actions = [
            action
            for action in preference_submenus["Robot"].actions()
            if not action.isSeparator()
        ]
        self.assertEqual(
            [action.text() for action in robot_actions[:2]],
            ["Follow recorded sequence", "Follow labels"],
        )
        self.assertIs(
            robot_actions[2].defaultWidget().findChild(QSlider),
            window.table_view.robot_speed_slider,
        )
        sound_actions = [
            action
            for action in preference_submenus["Sound"].actions()
            if not action.isSeparator()
        ]
        self.assertEqual(
            [action.text() for action in sound_actions[:1]],
            ["Play card sound"],
        )
        self.assertIs(sound_actions[0], window.table_view.robot_card_sound_action)
        self.assertIs(
            sound_actions[-1].defaultWidget().findChild(QSlider),
            window.table_view.sound_volume_slider,
        )
        with patch(
            "src.ui.main_window.QInputDialog.getItem",
            return_value=("中文", True),
        ):
            window.btn_language.click()
        self.assertEqual(
            [action.text() for action in window.menuBar().actions()],
            ["管理员", "偏好设置", "工具", "测试", "资源管理器"],
        )
        self.assertEqual(
            [action.text() for action in window.preference_menu.actions()],
            ["DDS", "样式", "机器人", "音效", "视图"],
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
                "Set my account expiration",
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
        self.assertTrue(window.table_view.robot_card_sound_action.isCheckable())
        self.assertTrue(window.table_view.robot_card_sound_action.isChecked())
        window.table_view.robot_card_sound_action.trigger()
        self.assertFalse(window.table_view.robot_card_sound_action.isChecked())
        self.assertFalse(window.table_view.robot_card_sound_enabled)
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
            [
                action.text()
                for action in window.explorer_menu.actions()
                if not action.isSeparator()
            ],
            ["README.md", "requirements.txt", "Labels"],
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
        window.active_admin_id = None

        self.assertFalse(window.action_export_admin_data.isEnabled())
        self.assertTrue(window.action_import_admin_data.isEnabled())
        window.set_language("zh")
        self.assertEqual(window.action_export_admin_data.text(), "导出管理员数据")
        self.assertEqual(window.action_import_admin_data.text(), "导入管理员数据")
        with patch.object(window, "_first_case_id", return_value=None):
            with patch.object(window.tree_view, "load_tree_data"):
                window._activate_admin(37, "transfer_admin")
        self.assertTrue(window.action_export_admin_data.isEnabled())
        self.assertTrue(window.action_import_admin_data.isEnabled())

    def test_export_tree_checks_descendants_and_allows_deselecting_a_child(self):
        dialog = ExportSelectionDialog(
            [
                {"type": "folder", "id": 1, "parent_id": None, "name": "Lessons"},
                {"type": "case", "id": 2, "folder_id": 1, "name": "Lessons / A"},
                {"type": "case", "id": 3, "folder_id": 1, "name": "Lessons / B"},
                {"type": "board", "id": 4, "case_id": 2, "name": "Board A"},
                {"type": "board", "id": 5, "case_id": 3, "name": "Board B"},
            ]
        )
        self.addCleanup(dialog.close)
        folder = dialog.asset_tree.topLevelItem(0)
        folder.setCheckState(0, Qt.CheckState.Checked)
        self.assertEqual(
            dialog.selected_assets(),
            {"folders": [1], "cases": [2, 3], "boards": [4, 5], "tests": []},
        )

        folder.child(0).setCheckState(0, Qt.CheckState.Unchecked)
        self.assertEqual(
            dialog.selected_assets(),
            {"folders": [], "cases": [3], "boards": [5], "tests": []},
        )

    def test_export_prompts_twice_and_saves_encrypted_package(self):
        window = MainWindow()
        self.addCleanup(window.close)
        window.active_admin_id = 55
        export_path = "/tmp/bridge-workspace"
        def accept_export_dialog(dialog):
            dialog.asset_tree.topLevelItem(0).setCheckState(
                0,
                Qt.CheckState.Checked,
            )
            dialog.account_name_input.setText("content_owner")
            dialog.account_password_input.setText("content owner password")
            dialog.confirm_password_input.setText("content owner password")
            return QDialog.DialogCode.Accepted

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
            patch(
                "src.ui.main_window.exec_and_delete",
                side_effect=accept_export_dialog,
            ),
            patch("src.ui.main_window.show_message"),
        ):
            service_class.return_value.list_export_assets.return_value = [
                {"type": "folder", "id": 1, "name": "folder"},
            ]
            window.export_admin_data()

        service_class.assert_called_once_with(window.repo.db)
        service_class.return_value.list_export_assets.assert_called_once_with(55)
        service_class.return_value.export_admin_data.assert_called_once_with(
            55,
            f"{export_path}.bdtpack",
            "a strong portable passphrase",
            selection={
                "folders": [1],
                "cases": [],
                "boards": [],
                "tests": [],
            },
            destination_account={
                "name": "content_owner",
                "password": "content owner password",
            },
        )

    def test_import_verifies_and_confirms_before_adding_package(self):
        window = MainWindow()
        self.addCleanup(window.close)
        window.active_admin_id = None
        window.active_admin_name = None
        payload = {
            "source_administrator": "sender",
            "destination_administrator": {
                "Name": "recipient",
                "Password": hash_password("recipient password"),
            },
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
            patch.object(window, "_activate_admin") as activate_admin,
        ):
            service_class.return_value.read_package.return_value = payload
            service_class.return_value.import_admin_data.return_value = {
                "destination_administrator_id": 88,
            }
            window.import_admin_data()

        service_class.return_value.read_package.assert_called_once_with(
            "/tmp/workspace.bdtpack",
            "a strong portable passphrase",
        )
        service_class.return_value.import_admin_data.assert_called_once_with(
            None,
            payload,
        )
        activate_admin.assert_called_once_with(88, "recipient")

    def test_explorer_actions_localize_and_reuse_chinese_readme(self):
        window = MainWindow()
        self.addCleanup(window.close)

        window.set_language("zh")
        self.assertEqual(
            [
                action.text()
                for action in window.explorer_menu.actions()
                if not action.isSeparator()
            ],
            ["项目说明（README.md）", "依赖清单（requirements.txt）", "标签"],
        )

        with patch("src.ui.main_window.ProjectDocumentDialog") as document_class:
            window.show_project_document("README.md")

        title, contents = document_class.call_args.args[:2]
        self.assertEqual(title, "项目说明（README.md）")
        self.assertIn("# 桥牌演示工具", contents)
        document_class.return_value.exec.assert_called_once()

        window.set_language("en")
        self.assertEqual(
            [
                action.text()
                for action in window.explorer_menu.actions()
                if not action.isSeparator()
            ],
            ["README.md", "requirements.txt", "Labels"],
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
