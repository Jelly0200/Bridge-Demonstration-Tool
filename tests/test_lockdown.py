import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication, QDialog, QLabel, QTableWidget

from src.core.bridge_game import BridgeGameEngine
from src.database.db_manager import DatabaseManager
from src.database.repository import Repository
from src.ui.main_window import (
    MainWindow,
    StudentIdentityDialog,
    StudentLoginDialog,
)
from src.ui.dialogs.test_scenario_dialog import TestScenarioDialog


class TestLockdown(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        DatabaseManager._instance = None
        self.temp_dir = tempfile.TemporaryDirectory()
        DatabaseManager(os.path.join(self.temp_dir.name, "lockdown.db"))
        self.repo = Repository()
        self.admin_id = self.repo.create_admin("lock_admin", "secure password")
        self.window = MainWindow()
        self.window._activate_admin(self.admin_id, "lock_admin")
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        self.window.table_view._stop_robot_playback()
        self.window.close()
        DatabaseManager._instance = None
        self.temp_dir.cleanup()

    def test_lockdown_requires_password_and_restores_the_normal_shell(self):
        self.assertTrue(self.window.toolbar.isHidden())
        self.assertFalse(self.window.menuBar().isHidden())

        with patch(
            "src.ui.main_window.QInputDialog.getText",
            return_value=("secure password", True),
        ):
            self.assertTrue(self.window.enter_lockdown())

        self.assertTrue(self.window.lockdown_active)
        self.assertEqual(self.window.current_mode, "LOCKDOWN")
        self.assertIs(
            self.window.left_stack.currentWidget(),
            self.window.lockdown_terminal,
        )
        self.assertTrue(self.window.toolbar.isHidden())
        self.assertTrue(self.window.menuBar().isHidden())
        self.assertTrue(self.window.table_view.btn_view_mode.isHidden())

        with patch(
            "src.ui.main_window.QInputDialog.getText",
            side_effect=AssertionError("Exit must not request another password"),
        ):
            self.window.execute_lockdown_command("Exit")

        self.assertFalse(self.window.lockdown_active)
        self.assertIsNone(self.window.active_admin_id)
        self.assertIsNone(self.window.active_admin_name)
        self.assertIs(self.window.left_stack.currentWidget(), self.window.left_widget)
        self.assertTrue(self.window.toolbar.isHidden())
        self.assertFalse(self.window.menuBar().isHidden())
        self.assertFalse(self.window.table_view.btn_view_mode.isHidden())
        self.assertIsNone(self.window.table_view.scenario)
        self.assertEqual(self.window.tree_view.topLevelItemCount(), 1)
        self.assertEqual(
            self.window.tree_view.topLevelItem(0).text(0),
            "Sign in or register to manage administrator assets.",
        )

    def test_test_scenario_uses_label_rule_hidden_view_and_robot_even_if_targeted(self):
        hands = {
            "NORTH": "AKQJ.T98.765.432",
            "EAST": "432.AKQJ.T98.765",
            "SOUTH": "T98.765.AKQJ.T98",
            "WEST": "765.432.432.AKQJ",
        }
        folder_id = self.repo.create_folder(self.admin_id, None, "Lessons")
        case_id = self.repo.create_case(folder_id, "Signals")
        board_id = self.repo.save_board(
            case_id,
            hands,
            "SOUTH",
            "NONE",
            description="Board One",
        )
        game = BridgeGameEngine(hands, dealer="SOUTH")
        game.start_play("1NT", "SOUTH")
        target_sequence = []
        while any(any(cards for cards in hand.values()) for hand in game.hands.values()):
            player = game.current_player
            card = game.get_legal_cards(player)[0]
            target_sequence.append(card)
            self.assertTrue(game.play_card(player, card))
        scenario_id = self.repo.create_scenario(
            board_id,
            "1NT PASS PASS PASS",
            "SOUTH",
            "1NT",
            "DOUBLE",
            1,
            json.dumps(target_sequence),
            name="Opening lead",
            information="Keep the auction and vulnerability settings.",
        )
        self.repo.replace_labels(
            scenario_id,
            [{"Sequence": 1, "Color": "RED", "Card": "SA"}],
        )

        self.window._load_lockdown_scenario(scenario_id, test_mode=True)

        self.assertTrue(self.window.table_view.test_playback_active)
        self.assertEqual(self.window.table_view.rule_mode, "LABEL")
        self.assertEqual(self.window.table_view.view_mode, "HIDDEN")
        self.assertEqual(
            self.window.table_view.scenario.bidding_route,
            "1NT PASS PASS PASS",
        )
        self.assertEqual(self.window.table_view.scenario.risk_status, "DOUBLE")
        self.assertEqual(
            self.window.table_view.scenario.information,
            "Keep the auction and vulnerability settings.",
        )
        self.assertEqual(
            self.window.table_view.bidding_route,
            ["1NT", "PASS", "PASS", "PASS"],
        )
        self.assertEqual(
            self.window.table_view.configuration.dealer,
            "SOUTH",
        )
        self.assertEqual(
            self.window.table_view.configuration.vulnerability,
            "NONE",
        )
        self.assertEqual(
            self.window.table_view.current_mode,
            "DEMONSTRATION",
        )
        self.assertIsNotNone(self.window.table_view.robot)
        self.assertEqual(self.window.table_view.scenario.is_targeted, 1)
        self.assertEqual(self.window.table_view.scenario.contract, "1NT")
        self.assertEqual(self.window.table_view.scenario.declarer, "SOUTH")
        self.assertEqual(self.window.table_view.game.risk_status, "DOUBLE")
        self.assertEqual(
            self.window.table_view.target_sequence,
            target_sequence,
        )
        self.assertEqual(
            self.window.table_view.labels,
            [{"Sequence": 1, "Color": "RED", "Card": "SA"}],
        )
        self.assertTrue(
            all(
                card.label_color == "NONE"
                and card.label_sequence is None
                for hand in self.window.table_view.hand_widgets.values()
                for card in hand.cards
            )
        )

        dialogs = []

        def capture_settings_dialog(*args, **kwargs):
            dialog = TestScenarioDialog(*args, **kwargs)
            dialogs.append(dialog)
            return dialog

        with (
            patch(
                "src.ui.views.table_view.TestScenarioDialog",
                side_effect=capture_settings_dialog,
            ),
            patch(
                "src.ui.views.table_view.BiddingBoxDialog",
                side_effect=AssertionError(
                    "Test settings must not open the auction editor."
                ),
            ),
            patch.object(QDialog, "exec", return_value=0),
        ):
            self.window.table_view.open_settings()

        settings = dialogs[0]
        self.addCleanup(settings.close)
        self.assertEqual(
            [
                label.text()
                for label in settings.findChildren(QLabel)
                if label.objectName() == "metricValue"
            ],
            ["1NT PASS PASS PASS"],
        )
        self.assertEqual(
            [
                label.text()
                for label in settings.findChildren(QLabel)
                if label.objectName() == "informationText"
            ],
            ["Keep the auction and vulnerability settings."],
        )
        self.assertEqual(settings.findChildren(QTableWidget), [])

    def test_test_run_selects_one_candidate_scenario_for_each_problem(self):
        test = {
            "id": 42,
            "name": "Choice test",
            "problems": [
                {"scenario_ids": [10, 11], "scores": {}},
                {"scenario_ids": [20, 21, 22], "scores": {}},
            ],
        }
        authenticated_student = {"id": 7, "name": "Student"}
        with (
            patch(
                "src.database.repository.Repository.get_test_by_name",
                return_value=test,
            ),
            patch(
                "src.ui.main_window.random.choice",
                side_effect=lambda values: values[-1],
            ),
            patch("src.ui.main_window.StudentIdentityDialog") as dialog_class,
            patch(
                "src.database.repository.Repository.get_available_tests_for_student",
                return_value=[{"id": 42, "name": "Choice test"}],
            ),
            patch.object(self.window, "_start_next_test_scenario"),
        ):
            dialog_class.return_value.exec.return_value = 1
            dialog_class.return_value.authenticated_student = authenticated_student
            self.window.start_lockdown_test("Choice test")

        self.assertEqual(
            [entry["scenario_id"] for entry in self.window.lockdown_scenarios],
            [11, 22],
        )
        self.assertEqual(
            len(self.window.lockdown_scenarios),
            len(test["problems"]),
        )

    def test_student_login_enters_lockdown_and_shows_assigned_tests(self):
        student_id = self.repo.create_student("Student One", "secure password")
        folder_id = self.repo.create_folder(self.admin_id, None, "Lessons")
        case_id = self.repo.create_case(folder_id, "Signals")
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
            board_id,
            "",
            "SOUTH",
            "4H",
            "NONE",
            0,
            "[]",
            name="Opening lead",
        )
        test_id = self.repo.save_test(
            self.admin_id,
            "Skills quiz",
            [
                {
                    "source_type": "case",
                    "case_id": case_id,
                    "scenario_ids": [scenario_id],
                    "contracts": ["4H"],
                    "results": ["="],
                    "scores": {"4H": {"=": 10}},
                }
            ],
        )
        self.repo.assign_test_to_student(self.admin_id, student_id, test_id)

        with patch("src.ui.main_window.StudentLoginDialog") as dialog_class:
            dialog_class.return_value.exec.return_value = 1
            dialog_class.return_value.authenticated_student = {
                "id": student_id,
                "name": "Student One",
            }
            self.window.student_login()

        self.assertTrue(self.window.lockdown_active)
        self.assertTrue(self.window.lockdown_student_session)
        self.assertEqual(self.window.lockdown_student_id, student_id)
        self.assertTrue(self.window.menuBar().isHidden())
        self.assertIn(
            "Skills quiz",
            self.window.lockdown_terminal.output.toPlainText(),
        )
        self.assertIn(
            "Run {TestName}",
            self.window.lockdown_terminal.output.toPlainText(),
        )

        self.window.execute_lockdown_command(
            "Run (Board One) Opening lead"
        )
        self.assertIn(
            "only run tests assigned",
            self.window.lockdown_terminal.output.toPlainText(),
        )

        with patch(
            "src.ui.main_window.QInputDialog.getText",
            side_effect=AssertionError("student exit must not request admin password"),
        ):
            self.window.execute_lockdown_command("Exit")
        self.assertFalse(self.window.lockdown_active)
        self.assertFalse(self.window.lockdown_student_session)
        self.assertIsNone(self.window.active_admin_id)
        self.assertIsNone(self.window.active_admin_name)
        self.assertFalse(self.window.menuBar().isHidden())

    def test_student_can_start_assigned_test_without_second_login_prompt(self):
        student_id = self.repo.create_student("Student Two", "secure password")
        self.window.lockdown_active = True
        self.window.lockdown_student_session = True
        self.window.lockdown_student_id = student_id
        self.window.lockdown_student_name = "Student Two"
        test = {
            "id": 42,
            "name": "Assigned quiz",
            "problems": [{"scenario_ids": [10], "scores": {}}],
        }
        with (
            patch(
                "src.database.repository.Repository.get_assigned_test_by_name",
                return_value=test,
            ),
            patch("src.ui.main_window.StudentIdentityDialog") as dialog_class,
            patch.object(self.window, "_start_next_test_scenario"),
        ):
            self.window.start_lockdown_test("Assigned quiz")

        dialog_class.assert_not_called()
        self.assertIs(self.window.lockdown_test, test)
        self.assertEqual(self.window.lockdown_student_id, student_id)

    def test_test_scenario_briefing_shows_route_and_information(self):
        self.window.lockdown_active = True
        self.window.lockdown_test = {"name": "Opening quiz"}
        self.window.lockdown_scenarios = [
            {
                "scenario_id": 25,
                "problem": {
                    "scenario_bidding_routes": {
                        25: "1NT PASS PASS PASS",
                    },
                    "scenario_information": {
                        25: "Use the auction to plan your defense.",
                    },
                    "scores": {},
                },
            }
        ]
        scenario = SimpleNamespace(
            bidding_route="1NT PASS PASS PASS",
            information="Use the auction to plan your defense.",
        )

        with (
            patch.object(self.window, "_save_active_scenario"),
            patch.object(
                self.window,
                "_load_lockdown_scenario",
                side_effect=lambda *_args, **_kwargs: setattr(
                    self.window.table_view,
                    "scenario",
                    scenario,
                ),
            ),
        ):
            self.window._start_next_test_scenario()

        output = self.window.lockdown_terminal.output.toPlainText()
        self.assertIn("Bidding: 1NT PASS PASS PASS", output)
        self.assertIn(
            "Scenario information: Use the auction to plan your defense.",
            output,
        )

    def test_test_result_dialog_is_styled_and_does_not_render_an_auction_table(self):
        dialog = TestScenarioDialog(
            "Scenario result",
            "Scenario complete",
            details=(("Contract", "1NT"), ("Scenario score", "10")),
            information="Review the play.",
            action_text="Proceed to next scenario",
        )
        self.addCleanup(dialog.close)

        self.assertIn("#0f172a", dialog.styleSheet())
        self.assertEqual(dialog.findChildren(QTableWidget), [])
        self.assertEqual(dialog.action_button.text(), "Proceed to next scenario")

        dialog.action_button.click()

        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)

    def test_student_identity_dialog_verifies_registered_student(self):
        student_id = self.repo.create_student("Registered student", "secure password")
        dialog = StudentIdentityDialog(self.repo, "Skills test", self.window)
        self.addCleanup(dialog.close)
        dialog.student_id.setText(str(student_id))
        dialog.student_key.setText("secure password")

        dialog._accept_if_valid()

        self.assertEqual(dialog.result(), 1)
        self.assertEqual(
            dialog.authenticated_student,
            {"id": student_id, "name": "Registered student"},
        )

    def test_student_login_dialog_verifies_registered_student(self):
        student_id = self.repo.create_student("Login student", "secure password")
        dialog = StudentLoginDialog(self.repo, self.window)
        self.addCleanup(dialog.close)
        dialog.student_id.setText(str(student_id))
        dialog.student_key.setText("secure password")

        dialog._accept_if_valid()

        self.assertEqual(dialog.result(), 1)
        self.assertEqual(
            dialog.authenticated_student,
            {"id": student_id, "name": "Login student"},
        )
