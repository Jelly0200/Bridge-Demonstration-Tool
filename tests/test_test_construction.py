import os
import tempfile
import unittest
from unittest.mock import patch

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QAbstractItemView, QHeaderView
from PyQt6.QtWidgets import QApplication, QLineEdit

from src.database.db_manager import DatabaseManager
from src.database.repository import Repository
from src.ui.main_window import (
    MainWindow,
    StudentManagementDialog,
    TestResultsDialog,
)
from src.ui.views.test_construction_view import TestProblemDialog
from src.ui.views.test_construction_view import TestConstructionView


class TestConstructionRepository(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        DatabaseManager._instance = None
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = DatabaseManager(
            os.path.join(self.temp_dir.name, "test_construction.db")
        )
        self.repo = Repository()
        self.admin_id = self.repo.create_admin("test_author", "secure password")
        folder_id = self.repo.create_folder(self.admin_id, None, "Lessons")
        self.case_id = self.repo.create_case(folder_id, "Card play")
        board_id = self.repo.save_board(
            self.case_id,
            {
                "SOUTH": "T98.765.AKQJ.T98",
                "WEST": "765.432.432.AKQJ",
                "NORTH": "AKQJ.T98.765.432",
                "EAST": "432.AKQJ.T98.765",
            },
            "SOUTH",
            "NONE",
        )
        self.scenario_ids = [
            self.repo.create_scenario(
                board_id,
                "",
                "SOUTH",
                "4H",
                "NONE",
                0,
                "[]",
                name=f"Scenario {index}",
            )
            for index in (1, 2)
        ]
        second_scenario = self.repo.get_scenario_by_id(self.scenario_ids[1])
        self.repo.update_scenario(
            second_scenario.id,
            second_scenario.bidding_route,
            second_scenario.declarer,
            "3NT",
            second_scenario.risk_status,
            second_scenario.is_targeted,
            second_scenario.targeted_sequence,
        )
        self.addCleanup(self._clean_up)

    def _clean_up(self):
        DatabaseManager._instance = None
        self.temp_dir.cleanup()

    def test_saves_and_loads_case_problems_with_scoring_matrix(self):
        first_scenario = self.repo.get_scenario_by_id(self.scenario_ids[0])
        self.repo.update_scenario(
            first_scenario.id,
            "1H PASS 4H PASS PASS PASS",
            first_scenario.declarer,
            first_scenario.contract,
            first_scenario.risk_status,
            first_scenario.is_targeted,
            first_scenario.targeted_sequence,
            "Read this before playing.",
        )
        test_id = self.repo.save_test(
            self.admin_id,
            "Defense quiz",
            [
                {
                    "source_type": "case",
                    "case_id": self.case_id,
                    "scenario_ids": self.scenario_ids,
                    "contracts": ["4H", "3NT"],
                    "results": ["=", "+1"],
                    "scores": {
                        "4H": {"=": 10, "+1": 20},
                        "3NT": {"=": 5, "+1": 15},
                    },
                },
                {
                    "source_type": "case",
                    "case_id": self.case_id,
                    "scenario_ids": [self.scenario_ids[1]],
                    "contracts": ["3NT"],
                    "results": ["=", "-1"],
                    "scores": {"3NT": {"=": 8, "-1": 3}},
                },
            ],
        )

        saved = self.repo.get_tests_by_admin(self.admin_id)
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["id"], test_id)
        self.assertEqual(saved[0]["name"], "Defense quiz")
        self.assertEqual(saved[0]["problems"][0]["scenario_ids"], self.scenario_ids)
        self.assertEqual(
            saved[0]["problems"][0]["scenario_information"][
                self.scenario_ids[0]
            ],
            "Read this before playing.",
        )
        self.assertEqual(
            saved[0]["problems"][0]["scenario_bidding_routes"][
                self.scenario_ids[0]
            ],
            "1H PASS 4H PASS PASS PASS",
        )
        self.assertEqual(saved[0]["problems"][0]["scores"]["4H"]["+1"], 20)
        self.assertEqual(len(saved[0]["problems"]), 2)
        self.assertEqual(
            saved[0]["problems"][1]["scores"]["3NT"]["-1"],
            3,
        )

        self.repo.save_test(
            self.admin_id,
            "Updated defense quiz",
            [
                {
                    "source_type": "case",
                    "case_id": self.case_id,
                    "scenario_ids": [self.scenario_ids[1]],
                    "contracts": ["3NT"],
                    "results": ["="],
                    "scores": {"3NT": {"=": 7}},
                }
            ],
            test_id,
        )
        updated = self.repo.get_tests_by_admin(self.admin_id)[0]
        self.assertEqual(updated["name"], "Updated defense quiz")
        self.assertEqual(updated["problems"][0]["scenario_ids"], [self.scenario_ids[1]])
        self.assertEqual(updated["problems"][0]["contracts"], ["3NT"])
        self.assertEqual(updated["problems"][0]["scores"]["3NT"]["="], 7)

    def test_rejects_scenarios_owned_by_another_administrator(self):
        other_admin_id = self.repo.create_admin("other_author", "secure password")
        other_folder_id = self.repo.create_folder(
            other_admin_id,
            None,
            "Private lessons",
        )
        other_case_id = self.repo.create_case(other_folder_id, "Private case")
        other_board_id = self.repo.save_board(
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
        private_scenario_id = self.repo.create_scenario(
            other_board_id,
            "",
            "SOUTH",
            "4H",
            "NONE",
            0,
            "[]",
        )
        with self.assertRaisesRegex(ValueError, "unavailable case"):
            self.repo.save_test(
                self.admin_id,
                "Unauthorized",
                [
                    {
                        "source_type": "case",
                        "case_id": other_case_id,
                        "scenario_ids": [private_scenario_id],
                        "contracts": ["4H"],
                        "results": ["="],
                        "scores": {"4H": {"=": 0}},
                    }
                ],
            )
        self.assertEqual(self.repo.get_tests_by_admin(self.admin_id), [])

    def test_repository_requires_derived_contracts_and_valid_stasis_values(self):
        with self.assertRaisesRegex(ValueError, "final contracts"):
            self.repo.save_test(
                self.admin_id,
                "Incorrect contract",
                [
                    {
                        "source_type": "case",
                        "case_id": self.case_id,
                        "scenario_ids": [self.scenario_ids[0]],
                        "contracts": ["3NT"],
                        "results": ["="],
                        "scores": {"3NT": {"=": 0}},
                    }
                ],
            )

        with self.assertRaisesRegex(ValueError, "invalid result stasis"):
            self.repo.save_test(
                self.admin_id,
                "Incorrect result",
                [
                    {
                        "source_type": "case",
                        "case_id": self.case_id,
                        "scenario_ids": [self.scenario_ids[0]],
                        "contracts": ["4H"],
                        "results": ["made"],
                        "scores": {"4H": {"made": 0}},
                    }
                ],
            )
        self.assertEqual(self.repo.get_tests_by_admin(self.admin_id), [])

    def test_student_password_authentication_and_test_result_link(self):
        student_id = self.repo.create_student("Ada Student", "student passphrase")
        self.assertIsNone(self.repo.authenticate_student(student_id, "wrong pass"))
        self.assertEqual(
            self.repo.authenticate_student(student_id, "student passphrase"),
            {"id": student_id, "name": "Ada Student"},
        )

        test_id = self.repo.save_test(
            self.admin_id,
            "Student-linked test",
            [
                {
                    "source_type": "case",
                    "case_id": self.case_id,
                    "scenario_ids": [self.scenario_ids[0]],
                    "contracts": ["4H"],
                    "results": ["="],
                    "scores": {"4H": {"=": 10}},
                }
            ],
        )
        self.repo.assign_test_to_student(self.admin_id, student_id, test_id)
        self.repo.save_test_result(
            test_id,
            student_id,
            [{"scenario_id": self.scenario_ids[0], "score": 10}],
            10,
        )
        result = self.db.get_connection().execute(
            "SELECT StudentId, ApplicantName FROM Test_Result"
        ).fetchone()
        self.assertEqual(result["StudentId"], student_id)
        self.assertEqual(result["ApplicantName"], "Ada Student")
        self.assertEqual(self.repo.get_available_tests_for_student(student_id), [])
        assignments = self.repo.get_student_test_assignments(self.admin_id)
        self.assertEqual(len(assignments), 1)
        self.assertIsNotNone(assignments[0]["completed_at"])
        with self.assertRaisesRegex(ValueError, "completed test assignment"):
            self.repo.remove_test_assignment(self.admin_id, student_id, test_id)
        with self.assertRaisesRegex(ValueError, "already completed"):
            self.repo.assign_test_to_student(self.admin_id, student_id, test_id)
        results = self.repo.get_test_results_by_admin(self.admin_id)
        self.assertEqual(results[0]["student_name"], "Ada Student")
        self.assertEqual(results[0]["test_name"], "Student-linked test")

    def test_student_test_assignment_can_be_removed_before_completion(self):
        student_id = self.repo.create_student("Assigned Student", "student passphrase")
        test_id = self.repo.save_test(
            self.admin_id,
            "Assigned quiz",
            [
                {
                    "source_type": "case",
                    "case_id": self.case_id,
                    "scenario_ids": [self.scenario_ids[0]],
                    "contracts": ["4H"],
                    "results": ["="],
                    "scores": {"4H": {"=": 10}},
                }
            ],
        )
        self.repo.assign_test_to_student(self.admin_id, student_id, test_id)

        self.assertEqual(
            self.repo.get_available_tests_for_student(student_id),
            [{"id": test_id, "name": "Assigned quiz"}],
        )
        with self.assertRaisesRegex(ValueError, "already assigned"):
            self.repo.assign_test_to_student(self.admin_id, student_id, test_id)
        self.repo.remove_test_assignment(self.admin_id, student_id, test_id)
        self.assertEqual(self.repo.get_available_tests_for_student(student_id), [])

    def test_student_management_and_test_results_dialogs_display_repository_data(self):
        student_id = self.repo.create_student("Managed Student", "student passphrase")
        test_id = self.repo.save_test(
            self.admin_id,
            "Managed quiz",
            [
                {
                    "source_type": "case",
                    "case_id": self.case_id,
                    "scenario_ids": [self.scenario_ids[0]],
                    "contracts": ["4H"],
                    "results": ["="],
                    "scores": {"4H": {"=": 10}},
                }
            ],
        )
        self.repo.assign_test_to_student(self.admin_id, student_id, test_id)
        management = StudentManagementDialog(self.repo, self.admin_id)
        self.addCleanup(management.close)

        self.assertIsNotNone(management.register_button)
        self.assertFalse(hasattr(management, "student_name_input"))
        self.assertFalse(hasattr(management, "student_password_input"))
        self.assertEqual(management.assignment_table.rowCount(), 1)
        self.assertEqual(management.assignment_table.item(0, 3).text(), "Available")
        self.assertEqual(management.student_combo.currentData(), student_id)
        self.assertEqual(management.test_combo.currentData(), test_id)

        management.assignment_table.selectRow(0)
        management._remove_assignment()
        self.assertEqual(management.assignment_table.rowCount(), 0)

        self.repo.assign_test_to_student(self.admin_id, student_id, test_id)
        self.repo.save_test_result(
            test_id,
            student_id,
            [{"scenario_id": self.scenario_ids[0], "score": 10}],
            10,
        )
        results = TestResultsDialog(self.repo, self.admin_id)
        self.addCleanup(results.close)
        self.assertEqual(results.results_table.rowCount(), 1)
        self.assertEqual(results.results_table.item(0, 1).text(), "Managed Student")
        self.assertEqual(results.results_table.item(0, 2).text(), "Managed quiz")

    def test_problem_dialog_derives_contracts_and_reads_stasis_scores(self):
        assets = self.repo.get_test_assets_by_admin(self.admin_id)
        editor = TestProblemDialog(assets)
        self.assertEqual(editor.matrix.rowCount(), 2)
        self.assertEqual(editor.matrix.verticalHeaderItem(1).text(), "3NT")
        editor.scenario_list.item(1).setCheckState(Qt.CheckState.Unchecked)
        editor.matrix.item(0, 0).setText("25")
        problem = editor._problem_data()

        self.assertEqual(problem["source_type"], "case")
        self.assertEqual(problem["case_id"], self.case_id)
        self.assertEqual(problem["scenario_ids"], [self.scenario_ids[0]])
        self.assertEqual(problem["contracts"], ["4H"])
        self.assertEqual(problem["results"], ["=", "-1", "-2", "+1", "+2"])
        self.assertEqual(problem["scores"]["4H"]["="], 25)

    def test_problem_score_matrix_uses_equal_row_and_column_sizes(self):
        editor = TestProblemDialog(
            self.repo.get_test_assets_by_admin(self.admin_id)
        )
        self.addCleanup(editor.close)

        self.assertEqual(
            editor.matrix.horizontalHeader().sectionResizeMode(0),
            QHeaderView.ResizeMode.Stretch,
        )
        self.assertEqual(
            editor.matrix.verticalHeader().sectionResizeMode(0),
            QHeaderView.ResizeMode.Stretch,
        )
        self.assertTrue(
            editor.matrix.editTriggers()
            & QAbstractItemView.EditTrigger.CurrentChanged
        )

    def test_problem_score_matrix_commits_active_edit_before_refresh(self):
        editor = TestProblemDialog(
            self.repo.get_test_assets_by_admin(self.admin_id)
        )
        self.addCleanup(editor.close)
        editor.show()
        self.application.processEvents()

        score_item = editor.matrix.item(0, 0)
        editor.matrix.editItem(score_item)
        self.application.processEvents()
        score_editor = editor.matrix.findChild(QLineEdit)
        self.assertIsNotNone(score_editor)
        score_editor.selectAll()
        QTest.keyClicks(score_editor, "25")
        self.assertEqual(score_item.text(), "0")

        editor._set_stasis(["=", "-1", "-2", "+1", "+2", "+3"])

        problem = editor._problem_data()
        self.assertEqual(problem["scores"]["4H"]["="], 25)
        self.assertEqual(problem["scores"]["4H"]["+3"], 0)

    def test_changing_case_combo_repopulates_scenarios_from_signal_index(self):
        second_case_id = self.repo.create_case(
            self.repo.get_folders_by_admin(self.admin_id)[0].id,
            "Second case",
        )
        second_board_id = self.repo.save_board(
            second_case_id,
            {
                "SOUTH": "T98.765.AKQJ.T98",
                "WEST": "765.432.432.AKQJ",
                "NORTH": "AKQJ.T98.765.432",
                "EAST": "432.AKQJ.T98.765",
            },
            "SOUTH",
            "NONE",
        )
        second_scenario_id = self.repo.create_scenario(
            second_board_id,
            "",
            "SOUTH",
            "2S",
            "NONE",
            0,
            "[]",
            name="Second-case scenario",
        )
        editor = TestProblemDialog(
            self.repo.get_test_assets_by_admin(self.admin_id)
        )

        editor.case_combo.setCurrentIndex(
            editor.case_combo.findData(second_case_id)
        )

        self.assertEqual(editor.scenario_list.count(), 1)
        self.assertEqual(
            editor.scenario_list.item(0).data(Qt.ItemDataRole.UserRole),
            second_scenario_id,
        )
        self.assertEqual(editor._problem_data()["contracts"], ["2S"])

    def test_problem_list_supports_add_edit_and_remove(self):
        view = TestConstructionView()
        view.set_admin_id(self.admin_id)
        view.new_test()
        problem = {
            "case_id": self.case_id,
            "scenario_ids": [self.scenario_ids[0]],
            "contracts": ["4H"],
            "results": ["="],
            "scores": {"4H": {"=": 5}},
        }
        with patch.object(view, "_open_problem_dialog", return_value=problem):
            view.add_problem()
        self.assertEqual(view.problem_list.count(), 1)

        updated_problem = {
            **problem,
            "scores": {"4H": {"=": 12}},
        }
        with patch.object(
            view,
            "_open_problem_dialog",
            return_value=updated_problem,
        ):
            view.edit_problem()
        self.assertEqual(
            view.problem_list.item(0).data(Qt.ItemDataRole.UserRole)["scores"],
            updated_problem["scores"],
        )
        view.remove_problem()
        self.assertEqual(view.problem_list.count(), 0)

    def test_main_window_opens_and_closes_test_construction_mode(self):
        window = MainWindow()
        self.addCleanup(window.close)
        window.active_admin_id = self.admin_id

        window.set_mode("TEST")

        self.assertEqual(window.current_mode, "TEST")
        self.assertIs(
            window.content_stack.currentWidget(),
            window.test_construction_view,
        )
        self.assertEqual(window.test_construction_view.admin_id, self.admin_id)

        window.test_construction_view.close_button.click()

        self.assertEqual(window.current_mode, "NORMAL")
        self.assertIs(window.content_stack.currentWidget(), window.table_view)


if __name__ == "__main__":
    unittest.main()
