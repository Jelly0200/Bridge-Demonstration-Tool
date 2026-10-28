import os
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QLineEdit,
    QMessageBox,
    QTreeWidgetItem,
)

from src.database.db_manager import DatabaseManager
from src.database.repository import Repository
from src.security.passwords import is_password_hash
from src.ui.dialogs.admin_registration_dialog import AdminRegistrationDialog
from src.ui.dialogs.instructions_dialog import InstructionsDialog
from src.ui.dialogs.monitor_dialog import MonitorDialog
from src.ui.main_window import MainWindow
from src.ui.views.tree_view import TreeView


class TestAdminRegistration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        DatabaseManager._instance = None
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        DatabaseManager(os.path.join(self.temp_dir.name, "accounts.db"))
        self.repo = Repository()

    def tearDown(self):
        DatabaseManager._instance = None

    def test_registration_hashes_password_and_creates_initial_workspace(self):
        admin_id, case_id = self.repo.register_admin("teacher", "correct horse")

        admin = self.repo.get_admin_by_name("teacher")
        self.assertEqual(admin.id, admin_id)
        self.assertTrue(is_password_hash(admin.password))
        self.assertNotEqual(admin.password, "correct horse")
        self.assertEqual(
            self.repo.authenticate_admin("teacher", "correct horse").id,
            admin_id,
        )
        self.assertIsNone(
            self.repo.authenticate_admin("teacher", "incorrect password")
        )

        folders = self.repo.get_folders_by_admin(admin_id)
        self.assertEqual(len(folders), 1)
        cases = self.repo.get_cases_by_folder(folders[0].id)
        self.assertEqual([case.id for case in cases], [case_id])

    def test_duplicate_registration_is_rejected_without_partial_workspace(self):
        self.repo.register_admin("teacher", "correct horse")

        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.register_admin("teacher", "another password")

        admin = self.repo.get_admin_by_name("teacher")
        folders = self.repo.get_folders_by_admin(admin.id)
        self.assertEqual(len(folders), 1)
        self.assertEqual(len(self.repo.get_cases_by_folder(folders[0].id)), 1)

    def test_monitor_includes_current_admin_and_shows_each_admin_counts(self):
        current_admin_id, _ = self.repo.register_admin("current_admin", "current password")
        other_admin_id, other_case_id = self.repo.register_admin(
            "other_admin",
            "other password",
        )
        board_id = self.repo.save_board(
            other_case_id,
            {
                "SOUTH": "T98.765.AKQJ.T98",
                "WEST": "765.432.432.AKQJ",
                "NORTH": "AKQJ.T98.765.432",
                "EAST": "432.AKQJ.T98.765",
            },
            "SOUTH",
            "NONE",
        )
        scenario_id = self.repo.create_scenario(
            board_id,
            "1NT PASS PASS PASS",
            "SOUTH",
            "1NT",
            "NONE",
            0,
            None,
        )
        self.repo.replace_labels(
            scenario_id,
            [{"Sequence": 1, "Color": "RED", "Card": "S7"}],
        )

        dialog = MonitorDialog(
            self.repo,
            current_admin_id,
            {"runtime": "Undo snapshots: 2/64", "errors": []},
        )
        self.addCleanup(dialog.close)

        self.assertEqual(dialog.admin_combo.count(), 2)
        self.assertEqual(dialog.admin_combo.currentData(), current_admin_id)
        self.assertIn("current_admin", dialog.admin_combo.currentText())
        other_index = dialog.admin_combo.findData(other_admin_id)
        self.assertGreaterEqual(other_index, 0)
        dialog.admin_combo.setCurrentIndex(other_index)
        self.assertEqual(
            self.repo.get_administrator_asset_counts(other_admin_id),
            {
                "folders": 1,
                "cases": 1,
                "boards": 1,
                "scenarios": 1,
                "labels": 1,
            },
        )
        self.assertIn("Labels: 1", dialog.asset_counts_label.text())
        self.assertNotIn("Password", dialog.asset_counts_label.text())

    def test_monitor_includes_current_admin_when_no_other_admin_exists(self):
        current_admin_id = self.repo.create_admin("solo_admin", "long password")
        dialog = MonitorDialog(
            self.repo,
            current_admin_id,
            {"runtime": "Undo snapshots: 0/64", "errors": []},
        )
        self.addCleanup(dialog.close)

        self.assertTrue(dialog.admin_combo.isEnabled())
        self.assertEqual(dialog.admin_combo.count(), 1)
        self.assertEqual(dialog.admin_combo.currentData(), current_admin_id)
        self.assertEqual(
            dialog.asset_counts_label.text(),
            "Folders: 0    Cases: 0    Boards: 0\n"
            "Scenarios: 0    Labels: 0",
        )

    def test_instructions_dialog_uses_selected_language(self):
        english = InstructionsDialog("en")
        chinese = InstructionsDialog("zh")
        self.addCleanup(english.close)
        self.addCleanup(chinese.close)

        english_text = english.instructions.toPlainText()
        chinese_text = chinese.instructions.toPlainText()
        self.assertIn("Sign in to manage", english_text)
        self.assertIn("Tests", english_text)
        self.assertIn("Run (BoardName)ScenarioName", english_text)
        self.assertIn("Test > Generate test report", english_text)
        self.assertIn("Only **Red**", english.ENGLISH_INSTRUCTIONS)
        self.assertIn("绿色（序号升序）", chinese_text)
        self.assertIn("登录后可管理", chinese_text)
        self.assertIn("测试", chinese_text)
        self.assertIn("锁定模式与运行测试", chinese_text)
        self.assertIn("测试 > 生成测试报告", chinese_text)

    def test_toolbar_exposes_monitor_and_instructions_actions(self):
        admin_id = self.repo.create_admin("toolbar_admin", "long password")
        window = MainWindow()
        self.addCleanup(window.close)

        self.assertFalse(window.btn_monitor.isEnabled())
        self.assertTrue(window.btn_instructions.isEnabled())
        window._activate_admin(admin_id, "toolbar_admin")
        self.assertTrue(window.btn_monitor.isEnabled())

    def test_inline_rename_editor_uses_full_tree_column_and_readable_height(self):
        admin_id = self.repo.create_admin("rename_admin", "long password")
        self.repo.create_folder(
            admin_id,
            None,
            "A long asset name that should remain readable while renaming",
        )
        window = MainWindow()
        window.resize(1280, 800)
        self.addCleanup(window.close)
        window._activate_admin(admin_id, "rename_admin")
        window.show()
        QApplication.processEvents()

        item = window.tree_view.topLevelItem(0)
        window.tree_view.setCurrentItem(item)
        window.edit_asset()
        QApplication.processEvents()
        editor = window.tree_view.findChild(QLineEdit)

        self.assertIsNotNone(editor)
        self.assertGreaterEqual(
            editor.width(),
            window.tree_view.viewport().width() - 20,
        )
        self.assertGreaterEqual(editor.height(), 32)

    def test_asset_name_input_dialogs_have_readable_entry_fields(self):
        window = MainWindow()
        self.addCleanup(window.close)

        text_dialog = window._create_asset_text_dialog("New folder", "Folder name:")
        text_dialog.show()
        QApplication.processEvents()
        text_editor = text_dialog.findChild(QLineEdit)

        item_dialog = window._create_asset_choice_dialog(
            "Add to folder",
            "Choose what to add:",
            ["Create a case", "Create a child folder"],
        )
        item_dialog.show()
        QApplication.processEvents()
        combo_editor = item_dialog.findChild(QComboBox)
        self.addCleanup(text_dialog.close)
        self.addCleanup(item_dialog.close)

        self.assertGreaterEqual(text_dialog.width(), 520)
        self.assertIsNotNone(text_editor)
        self.assertGreaterEqual(text_editor.width(), 460)
        self.assertIsNotNone(combo_editor)
        self.assertGreaterEqual(combo_editor.width(), 460)

    def test_duplicate_asset_button_has_room_for_its_full_label(self):
        window = MainWindow()
        self.addCleanup(window.close)
        window.resize(1280, 800)
        window.show()
        QApplication.processEvents()

        duplicate_button = window.btn_duplicate_asset
        self.assertGreaterEqual(
            duplicate_button.width(),
            duplicate_button.sizeHint().width(),
        )

    def test_tree_controls_and_zoom_are_scoped_to_their_own_tree(self):
        first_window = MainWindow()
        second_window = MainWindow()
        self.addCleanup(second_window.close)
        self.addCleanup(first_window.close)

        first_tree = first_window.tree_view
        second_tree = second_window.tree_view
        first_folder = QTreeWidgetItem(first_tree, ["First folder"])
        QTreeWidgetItem(first_folder, ["First child"])
        second_folder = QTreeWidgetItem(second_tree, ["Second folder"])
        QTreeWidgetItem(second_folder, ["Second child"])

        first_window.btn_expand_all_folders.click()
        self.assertTrue(first_folder.isExpanded())
        self.assertFalse(second_folder.isExpanded())

        second_folder.setExpanded(True)
        first_window.btn_collapse_all_folders.click()
        self.assertFalse(first_folder.isExpanded())
        self.assertTrue(second_folder.isExpanded())

        QTest.keyClick(
            first_tree,
            Qt.Key.Key_Plus,
            Qt.KeyboardModifier.ControlModifier,
        )
        self.assertIsNotNone(first_tree._tree_zoom_font_size_px)
        self.assertIsNone(second_tree._tree_zoom_font_size_px)
        QTest.keyClick(
            first_tree,
            Qt.Key.Key_0,
            Qt.KeyboardModifier.ControlModifier,
        )
        self.assertIsNone(first_tree._tree_zoom_font_size_px)

    def test_asset_types_have_distinct_tree_icons_and_colors(self):
        tree = TreeView()
        self.addCleanup(tree.close)
        items = {}
        for asset_type in tree.ASSET_PRESENTATION:
            item = QTreeWidgetItem(tree, [asset_type])
            item.setData(0, Qt.ItemDataRole.UserRole, (asset_type, 1))
            tree._style_asset_item(item, asset_type)
            items[asset_type] = item

        colors = {
            item.foreground(0).color().name()
            for item in items.values()
        }
        self.assertEqual(len(colors), len(items))
        self.assertTrue(all(not item.icon(0).isNull() for item in items.values()))

        tree.set_language("zh")
        self.assertEqual(items["folder"].toolTip(0), "文件夹资源")

    def test_legacy_plaintext_password_is_upgraded_after_successful_login(self):
        connection = DatabaseManager._instance.get_connection()
        try:
            connection.execute(
                "INSERT INTO Administration (Name, Password) VALUES (?, ?)",
                ("legacy", "legacy password"),
            )
            connection.commit()
        finally:
            connection.close()

        self.assertIsNotNone(
            self.repo.authenticate_admin("legacy", "legacy password")
        )
        self.assertTrue(
            is_password_hash(self.repo.get_admin_by_name("legacy").password)
        )

    def test_registration_dialog_creates_account_and_accepts(self):
        dialog = AdminRegistrationDialog()
        dialog.username_input.setText("new_teacher")
        dialog.password_input.setText("safe password")
        dialog.confirm_password_input.setText("safe password")

        with patch(
            "src.ui.dialogs.admin_registration_dialog.QMessageBox.information"
        ):
            dialog.register()

        self.assertEqual(dialog.result(), dialog.DialogCode.Accepted)
        self.assertIsNotNone(
            self.repo.authenticate_admin("new_teacher", "safe password")
        )
        dialog.close()

    def test_registration_dialog_rejects_password_mismatch(self):
        dialog = AdminRegistrationDialog()
        dialog.username_input.setText("new_teacher")
        dialog.password_input.setText("safe password")
        dialog.confirm_password_input.setText("different password")

        with patch(
            "src.ui.dialogs.admin_registration_dialog.QMessageBox.warning"
        ) as warning:
            dialog.register()

        warning.assert_called_once()
        self.assertIsNone(self.repo.get_admin_by_name("new_teacher"))
        dialog.close()

    def test_toolbar_registration_activates_new_account_workspace(self):
        self.repo.register_admin("existing_admin", "existing password")
        admin_id, case_id = self.repo.register_admin("new_admin", "new password")
        new_admin_folder = self.repo.get_folders_by_admin(admin_id)[0]
        nested_folder_id = self.repo.create_folder(
            admin_id,
            new_admin_folder.id,
            "Nested materials",
        )

        window = MainWindow()
        self.addCleanup(window.close)
        registration_dialog = Mock()
        registration_dialog.exec.return_value = True
        registration_dialog.admin_id = admin_id
        registration_dialog.default_case_id = case_id

        with patch(
            "src.ui.main_window.AdminRegistrationDialog",
            return_value=registration_dialog,
        ):
            window.btn_register.click()

        self.assertEqual(window.active_admin_id, admin_id)
        self.assertEqual(window.active_case_id, case_id)
        self.assertEqual(window.tree_view.topLevelItemCount(), 1)
        root_item = window.tree_view.topLevelItem(0)
        nested_item = next(
            root_item.child(index)
            for index in range(root_item.childCount())
            if root_item.child(index).data(
                0,
                Qt.ItemDataRole.UserRole,
            ) == ("folder", nested_folder_id)
        )
        self.assertEqual(nested_item.text(0), "Nested materials")

    def test_edit_button_opens_board_editor_without_a_separate_board_button(self):
        admin_id = self.repo.create_admin("asset_admin", "long password")
        folder_id = self.repo.create_folder(admin_id, None, "Lessons")
        case_id = self.repo.create_case(folder_id, "Case")
        hands = {
            "SOUTH": "T98.765.AKQJ.T98",
            "WEST": "765.432.432.AKQJ",
            "NORTH": "AKQJ.T98.765.432",
            "EAST": "432.AKQJ.T98.765",
        }
        board_id = self.repo.save_board(
            case_id,
            hands,
            "SOUTH",
            "NONE",
        )
        self.repo.create_scenario(
            board_id,
            "1NT PASS PASS PASS",
            "SOUTH",
            "1NT",
            "NONE",
            0,
            None,
        )
        window = MainWindow()
        self.addCleanup(window.close)
        window._activate_admin(admin_id, "asset_admin")
        folder_item = window.tree_view.topLevelItem(0)
        case_item = folder_item.child(0)
        board_item = case_item.child(0)
        scenario_item = board_item.child(0)

        window.tree_view.setCurrentItem(board_item)
        self.assertFalse(hasattr(window, "btn_board_edit"))
        self.assertTrue(window.btn_edit_asset.isEnabled())
        with patch.object(window, "_open_board_editor") as open_editor:
            window.btn_edit_asset.click()
        open_editor.assert_called_once_with(board_id=board_id)

    def test_editing_scenario_name_is_inline_and_persisted(self):
        admin_id = self.repo.create_admin("scenario_rename_admin", "long password")
        folder_id = self.repo.create_folder(admin_id, None, "Lessons")
        case_id = self.repo.create_case(folder_id, "Case")
        board_id = self.repo.save_board(
            case_id,
            {
                "SOUTH": "T98.765.AKQJ.T98",
                "WEST": "765.432.432.AKQJ",
                "NORTH": "AKQJ.T98.765.432",
                "EAST": "432.AKQJ.T98.765",
            },
            "SOUTH",
            "NONE",
        )
        scenario_id = self.repo.create_scenario(
            board_id, "", "SOUTH", "", "NONE", 0, "[]"
        )
        window = MainWindow()
        self.addCleanup(window.close)
        window._activate_admin(admin_id, "scenario_rename_admin")
        scenario_item = window._find_asset_item(("scenario", scenario_id))

        window.tree_view.setCurrentItem(scenario_item)
        window.btn_edit_asset.click()
        scenario_item.setText(0, "Opening lead lesson")

        self.assertEqual(
            self.repo.get_scenario_by_id(scenario_id).name,
            "Opening lead lesson",
        )

    def test_add_on_folder_offers_case_or_child_folder(self):
        admin_id = self.repo.create_admin("folder_admin", "long password")
        folder_id = self.repo.create_folder(admin_id, None, "Lessons")
        window = MainWindow()
        self.addCleanup(window.close)
        window._activate_admin(admin_id, "folder_admin")
        folder_item = window.tree_view.topLevelItem(0)
        window.tree_view.setCurrentItem(folder_item)

        with (
            patch(
                "src.ui.main_window.MainWindow._prompt_asset_choice",
                return_value=("Create a case", True),
            ) as choose_action,
            patch(
                "src.ui.main_window.MainWindow._prompt_asset_name",
                return_value=("Opening leads", True),
            ),
        ):
            window.btn_add_asset.click()
        choose_action.assert_called_once()
        self.assertEqual(
            [case.name for case in self.repo.get_cases_by_folder(folder_id)],
            ["Opening leads"],
        )

        folder_item = window.tree_view.topLevelItem(0)
        window.tree_view.setCurrentItem(folder_item)
        with (
            patch(
                "src.ui.main_window.MainWindow._prompt_asset_choice",
                return_value=("Create a child folder", True),
            ),
            patch(
                "src.ui.main_window.MainWindow._prompt_asset_name",
                return_value=("Advanced lessons", True),
            ),
        ):
            window.btn_add_asset.click()
        folders = self.repo.get_folders_by_admin(admin_id)
        child_folder = next(folder for folder in folders if folder.name == "Advanced lessons")
        self.assertEqual(child_folder.parent_folder_id, folder_id)

    def test_add_on_case_opens_board_editor_without_asking(self):
        admin_id = self.repo.create_admin("case_admin", "long password")
        folder_id = self.repo.create_folder(admin_id, None, "Lessons")
        case_id = self.repo.create_case(folder_id, "Case")
        window = MainWindow()
        self.addCleanup(window.close)
        window._activate_admin(admin_id, "case_admin")
        case_item = window.tree_view.topLevelItem(0).child(0)
        window.tree_view.setCurrentItem(case_item)

        with (
            patch.object(window, "_prompt_asset_choice") as chooser,
            patch.object(window, "_open_board_editor") as open_editor,
        ):
            window.btn_add_asset.click()

        chooser.assert_not_called()
        open_editor.assert_called_once_with(case_id=case_id)

    def test_move_asset_requires_review_and_moves_only_after_confirmation(self):
        admin_id = self.repo.create_admin("move_ui_admin", "long password")
        first_folder_id = self.repo.create_folder(admin_id, None, "First")
        second_folder_id = self.repo.create_folder(admin_id, None, "Second")
        case_id = self.repo.create_case(first_folder_id, "Opening")
        second_case_id = self.repo.create_case(second_folder_id, "Defense")
        window = MainWindow()
        self.addCleanup(window.close)
        window._activate_admin(admin_id, "move_ui_admin")

        case_item = window._find_asset_item(("case", case_id))
        window.tree_view.setCurrentItem(case_item)
        self.assertTrue(window.btn_move_asset.isEnabled())
        destinations = window._asset_move_destinations("case", case_id)
        self.assertEqual(len(destinations), 1)

        with (
            patch.object(
                window,
                "_prompt_asset_choice",
                return_value=(destinations[0][0], True),
            ) as choose_destination,
            patch(
                "src.ui.main_window.show_message",
                return_value=QMessageBox.StandardButton.No,
            ) as review_move,
        ):
            window.btn_move_asset.click()

        choose_destination.assert_called_once()
        self.assertIn("From: First / Opening", review_move.call_args.args[3])
        self.assertIn("To: Second / Opening", review_move.call_args.args[3])
        self.assertEqual(
            self.repo.get_case_by_id(case_id).folder_id,
            first_folder_id,
        )

        second_case_item = window._find_asset_item(("case", second_case_id))
        window.tree_view.setCurrentItem(second_case_item)
        destinations = window._asset_move_destinations("case", second_case_id)
        with (
            patch.object(
                window,
                "_prompt_asset_choice",
                return_value=(destinations[0][0], True),
            ),
            patch(
                "src.ui.main_window.show_message",
                return_value=QMessageBox.StandardButton.Yes,
            ),
        ):
            window.btn_move_asset.click()

        self.assertEqual(
            self.repo.get_case_by_id(second_case_id).folder_id,
            first_folder_id,
        )

    def test_creating_board_does_not_replace_the_loaded_table(self):
        admin_id = self.repo.create_admin("board_refresh_admin", "long password")
        folder_id = self.repo.create_folder(admin_id, None, "Lessons")
        case_id = self.repo.create_case(folder_id, "Case")
        board_id = self.repo.save_board(
            case_id,
            {
                "SOUTH": "T98.765.AKQJ.T98",
                "WEST": "765.432.432.AKQJ",
                "NORTH": "AKQJ.T98.765.432",
                "EAST": "432.AKQJ.T98.765",
            },
            "SOUTH",
            "NONE",
        )
        window = MainWindow()
        self.addCleanup(window.close)
        window._activate_admin(admin_id, "board_refresh_admin")
        board_item = window._find_asset_item(("board", board_id))
        window.tree_view.setCurrentItem(board_item)
        self.assertIsNone(window.table_view.board)

        board = self.repo.get_board_by_id(board_id)
        configuration = self.repo.get_board_configuration(
            board.board_configuration_id
        )
        window.table_view.load_board(board, configuration)
        loaded_game = window.table_view.game

        dialog = Mock()
        dialog.exec.return_value = True
        with patch(
            "src.ui.main_window.BoardEditorDialog",
            return_value=dialog,
        ):
            window._open_board_editor(case_id=case_id)

        self.assertIs(window.table_view.board, board)
        self.assertIs(window.table_view.game, loaded_game)

    def test_add_on_board_creates_and_loads_an_empty_scenario(self):
        admin_id = self.repo.create_admin("scenario_refresh_admin", "long password")
        folder_id = self.repo.create_folder(admin_id, None, "Lessons")
        case_id = self.repo.create_case(folder_id, "Case")
        board_id = self.repo.save_board(
            case_id,
            {
                "SOUTH": "T98.765.AKQJ.T98",
                "WEST": "765.432.432.AKQJ",
                "NORTH": "AKQJ.T98.765.432",
                "EAST": "432.AKQJ.T98.765",
            },
            "SOUTH",
            "NONE",
        )
        window = MainWindow()
        self.addCleanup(window.close)
        window._activate_admin(admin_id, "scenario_refresh_admin")

        window._create_scenario(board_id)

        scenarios = self.repo.get_scenarios_by_board(board_id)
        self.assertEqual(len(scenarios), 1)
        scenario = scenarios[0]
        scenario_id = scenario.id
        selected = window.tree_view.currentItem()
        self.assertEqual(
            selected.data(0, Qt.ItemDataRole.UserRole),
            ("scenario", scenario_id),
        )
        self.assertEqual(window.table_view.scenario.id, scenario_id)
        self.assertEqual(scenario.bidding_route, "")
        self.assertEqual(scenario.contract, "")
        self.assertEqual(scenario.targeted_sequence, "[]")
        self.assertEqual(self.repo.get_labels_by_scenario(scenario_id), [])
        self.assertEqual(window.table_view.labels, [])
        self.assertEqual(window.table_view.target_sequence, [])
        self.assertIsNone(window.table_view.robot)
        self.assertEqual(window.table_view.btn_mode.text(), "Mode: Normal")
        window.set_mode("DEMONSTRATION")
        self.assertEqual(window.current_mode, "NORMAL")

    def test_single_click_does_not_load_and_double_click_autosaves_scenario(self):
        admin_id = self.repo.create_admin("scenario_switch_admin", "long password")
        folder_id = self.repo.create_folder(admin_id, None, "Lessons")
        case_id = self.repo.create_case(folder_id, "Case")
        board_id = self.repo.save_board(
            case_id,
            {
                "SOUTH": "T98.765.AKQJ.T98",
                "WEST": "765.432.432.AKQJ",
                "NORTH": "AKQJ.T98.765.432",
                "EAST": "432.AKQJ.T98.765",
            },
            "SOUTH",
            "NONE",
        )
        first_scenario_id = self.repo.create_scenario(
            board_id, "", "SOUTH", "", "NONE", 0, "[]"
        )
        second_scenario_id = self.repo.create_scenario(
            board_id, "", "SOUTH", "", "NONE", 0, "[]"
        )
        window = MainWindow()
        self.addCleanup(window.close)
        window._activate_admin(admin_id, "scenario_switch_admin")
        window._load_scenario(first_scenario_id)
        active_scenario = window.table_view.scenario
        active_scenario.contract = "1NT"
        window.table_view.bidding_route = ["1NT", "PASS"]
        window.table_view.labels = [
            {"Sequence": 1, "Color": "RED", "Card": "AH"}
        ]

        second_item = window._find_asset_item(("scenario", second_scenario_id))
        window.tree_view.setCurrentItem(second_item)
        self.assertEqual(window.table_view.scenario.id, first_scenario_id)
        self.assertEqual(
            self.repo.get_scenario_by_id(first_scenario_id).contract,
            "",
        )

        window.on_asset_double_clicked("scenario", second_scenario_id)

        saved_scenario = self.repo.get_scenario_by_id(first_scenario_id)
        self.assertEqual(saved_scenario.contract, "1NT")
        self.assertEqual(saved_scenario.bidding_route, "1NT PASS")
        self.assertEqual(
            [
                (label.sequence, label.color, label.card)
                for label in self.repo.get_labels_by_scenario(first_scenario_id)
            ],
            [(1, "RED", "AH")],
        )
        self.assertEqual(window.table_view.scenario.id, second_scenario_id)
        self.assertEqual(window.table_view.bidding_route, [])

    def test_logout_clears_admin_assets_and_loaded_deal(self):
        admin_id = self.repo.create_admin("logout_admin", "long password")
        folder_id = self.repo.create_folder(admin_id, None, "Lessons")
        case_id = self.repo.create_case(folder_id, "Case")
        board_id = self.repo.save_board(
            case_id,
            {
                "SOUTH": "T98.765.AKQJ.T98",
                "WEST": "765.432.432.AKQJ",
                "NORTH": "AKQJ.T98.765.432",
                "EAST": "432.AKQJ.T98.765",
            },
            "SOUTH",
            "NONE",
        )
        board = self.repo.get_board_by_id(board_id)
        configuration = self.repo.get_board_configuration(
            board.board_configuration_id
        )
        window = MainWindow()
        self.addCleanup(window.close)
        window._activate_admin(admin_id, "logout_admin")
        window.table_view.load_board(board, configuration)
        self.assertEqual(window.table_view.board.id, board_id)

        window.btn_logout.click()

        self.assertIsNone(window.active_admin_id)
        self.assertEqual(window.admin_indicator.text(), "Administrator: Not signed in")
        self.assertIsNone(window.table_view.board)
        self.assertIsNone(window.table_view.game)
        self.assertFalse(window.btn_logout.isEnabled())
        self.assertEqual(window.tree_view.topLevelItemCount(), 1)
        self.assertIsNone(
            window.tree_view.topLevelItem(0).data(
                0,
                Qt.ItemDataRole.UserRole,
            )
        )


if __name__ == "__main__":
    unittest.main()
