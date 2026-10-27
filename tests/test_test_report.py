import os
import re
import tempfile
import unittest

from PyQt6.QtWidgets import QApplication, QGroupBox

from src.core.generate_test_report import generate_pdf_report
from src.database.db_manager import DatabaseManager
from src.database.repository import Repository
from src.ui.dialogs.test_report_dialog import TestReportDialog
from src.ui.i18n import BilingualTextController


class TestTestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        DatabaseManager._instance = None
        self.temp_dir = tempfile.TemporaryDirectory()
        DatabaseManager(os.path.join(self.temp_dir.name, "test_report.db"))
        self.repository = Repository()
        self.admin_id = self.repository.create_admin(
            "report_admin",
            "secure password",
        )
        folder_id = self.repository.create_folder(
            self.admin_id,
            None,
            "Lessons",
        )
        case_id = self.repository.create_case(folder_id, "Opening")
        self.scenario_ids = []
        for index, contract in enumerate(("4H", "4H", "3NT"), start=1):
            board_id = self.repository.save_board(
                case_id,
                {
                    "SOUTH": "T98.765.AKQJ.T98",
                    "WEST": "765.432.432.AKQJ",
                    "NORTH": "AKQJ.T98.765.432",
                    "EAST": "432.AKQJ.T98.765",
                },
                "SOUTH",
                "NONE",
                description=f"Board {index}",
            )
            self.scenario_ids.append(
                self.repository.create_scenario(
                    board_id,
                    "",
                    "SOUTH",
                    contract,
                    "NONE",
                    0,
                    "[]",
                    name=f"Scenario {index}",
                )
            )
        self.test_id = self.repository.save_test(
            self.admin_id,
            "Defense quiz",
            [
                {
                    "source_type": "case",
                    "case_id": case_id,
                    "scenario_ids": self.scenario_ids[:2],
                    "contracts": ["4H"],
                    "results": ["="],
                    "scores": {"4H": {"=": 10}},
                },
                {
                    "source_type": "case",
                    "case_id": case_id,
                    "scenario_ids": [self.scenario_ids[2]],
                    "contracts": ["3NT"],
                    "results": ["="],
                    "scores": {"3NT": {"=": 10}},
                },
            ],
        )
        self.student_ids = [
            self.repository.create_student(name, "student password")
            for name in ("Alice", "Bob", "Cara", "Drew")
        ]
        problem_scores = ((10, 20), (30, 10), (40, 10), (10, 10))
        problem_scenarios = (
            (self.scenario_ids[0], self.scenario_ids[2]),
            (self.scenario_ids[1], self.scenario_ids[2]),
            (self.scenario_ids[0], self.scenario_ids[2]),
            (self.scenario_ids[1], self.scenario_ids[2]),
        )
        for student_id, scores, scenario_ids in zip(
                self.student_ids,
                problem_scores,
                problem_scenarios,
        ):
            self.repository.assign_test_to_student(
                self.admin_id,
                student_id,
                self.test_id,
            )
            self.repository.save_test_result(
                self.test_id,
                student_id,
                [
                    {
                        "problem_number": number,
                        "scenario_id": scenario_id,
                        "contract": "4H" if number == 1 else "3NT",
                        "stasis": "=",
                        "score": score,
                    }
                    for number, (scenario_id, score) in enumerate(
                    zip(scenario_ids, scores),
                    start=1,
                )
                ],
                sum(scores),
            )
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        DatabaseManager._instance = None
        self.temp_dir.cleanup()

    def test_report_data_contains_admin_problems_results_and_scenarios(self):
        report = self.repository.get_test_report_data(self.admin_id)

        self.assertEqual(report["administrator"], "report_admin")
        self.assertEqual(len(report["tests"]), 1)
        self.assertEqual(
            [problem["sequence"] for problem in report["tests"][0]["problems"]],
            [1, 2],
        )
        self.assertEqual(len(report["results"]), 4)
        self.assertEqual(
            report["results"][0]["contracts"][0]["problem_number"],
            1,
        )
        self.assertEqual(
            report["scenarios"][self.scenario_ids[0]]["name"],
            "Scenario 1",
        )

    def test_report_dialog_builds_statistics_matrices_and_top_three(self):
        dialog = TestReportDialog(
            self.repository,
            self.admin_id,
        )
        self.addCleanup(dialog.close)

        self.assertEqual(dialog.stats_labels["Administrator"].text(), "report_admin")
        self.assertEqual(dialog.stats_labels["Test attempts"].text(), "4")
        self.assertEqual(dialog.stats_labels["Average score"].text(), "35.00")
        self.assertEqual(dialog.stats_labels["Mean score"].text(), "35.00")
        self.assertEqual(dialog.stats_labels["Median score"].text(), "35.00")
        self.assertEqual(dialog.stats_labels["Maximum score"].text(), "50")
        self.assertEqual(dialog.stats_labels["Minimum score"].text(), "20")

        ability = dialog.ability_table
        self.assertEqual(ability.columnCount(), 4)
        self.assertEqual(
            ability.horizontalHeaderItem(2).text(),
            "Defense quiz\nProblem 1",
        )
        alice_row = next(
            row
            for row in range(ability.rowCount())
            if ability.item(row, 1).text() == "Alice"
        )
        self.assertEqual(ability.item(alice_row, 2).text(), "10")
        self.assertEqual(ability.item(alice_row, 3).text(), "20")

        difficulty = dialog.scenario_table
        first_scenario_row = next(
            row
            for row in range(difficulty.rowCount())
            if "Scenario 1" in difficulty.item(row, 0).text()
        )
        self.assertEqual(difficulty.item(first_scenario_row, 2).text(), "25.00")
        self.assertEqual(difficulty.item(first_scenario_row, 4).text(), "2")

        top_three = dialog.top_three_table
        self.assertEqual(top_three.rowCount(), 3)
        self.assertEqual(
            [top_three.item(row, 2).text() for row in range(3)],
            ["Cara", "Bob", "Alice"],
        )

    def test_chinese_report_labels_and_pdf_generation(self):
        dialog = TestReportDialog(
            self.repository,
            self.admin_id,
            language="zh",
        )
        self.addCleanup(dialog.close)
        controller = BilingualTextController()
        controller.install(dialog)
        controller.set_language("zh")

        self.assertEqual(dialog.windowTitle(), "测试报告")
        self.assertEqual(
            dialog.ability_table.horizontalHeaderItem(1).text(),
            "考生",
        )
        self.assertIn(
            "场景难度统计",
            [group.title() for group in dialog.findChildren(QGroupBox)],
        )

        english_pdf = os.path.join(self.temp_dir.name, "report-en.pdf")
        chinese_pdf = os.path.join(self.temp_dir.name, "report-zh.pdf")
        generate_pdf_report(
            self.repository.get_test_report_data(self.admin_id),
            english_pdf,
        )
        generate_pdf_report(
            self.repository.get_test_report_data(self.admin_id),
            chinese_pdf,
            "zh",
        )
        for path in (english_pdf, chinese_pdf):
            with open(path, "rb") as pdf_file:
                pdf_contents = pdf_file.read()
            self.assertTrue(pdf_contents.startswith(b"%PDF"))
            self.assertGreaterEqual(
                len(re.findall(rb"/Type\s*/Page\b", pdf_contents)),
                3,
            )
            self.assertGreater(os.path.getsize(path), 1000)


if __name__ == "__main__":
    unittest.main()
