import unittest

from PyQt6.QtWidgets import QApplication, QLabel

from src.robot.label_evaluator import DEFAULT_COLOR_JOBS
from src.ui.dialogs.label_jobs_dialog import (
    LabelDefinitionDialog,
    LabelJobsDialog,
)


class TestLabelJobsDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_dialog_uses_documented_defaults_and_returns_edits(self):
        dialog = LabelJobsDialog()
        self.addCleanup(dialog.close)

        self.assertEqual(dialog.color_jobs, DEFAULT_COLOR_JOBS)
        red_lead = dialog.job_controls["leading", "RED"]
        red_lead.setCurrentIndex(red_lead.findData("OFF"))
        dialog.apply_button.click()

        self.assertEqual(dialog.result(), dialog.DialogCode.Accepted)
        self.assertEqual(dialog.color_jobs["leading"]["RED"], "OFF")

    def test_restore_defaults_restores_all_phases(self):
        dialog = LabelJobsDialog()
        self.addCleanup(dialog.close)
        dialog.job_controls["leading", "RED"].setCurrentIndex(
            dialog.job_controls["leading", "RED"].findData("OFF")
        )

        dialog.restore_button.click()

        self.assertEqual(
            dialog.job_controls["leading", "RED"].currentData(),
            DEFAULT_COLOR_JOBS["leading"]["RED"],
        )

    def test_definition_view_shows_phase_color_matrix_and_dds_behavior(self):
        dialog = LabelDefinitionDialog()
        self.addCleanup(dialog.close)

        self.assertEqual(dialog.matrix.rowCount(), 3)
        self.assertEqual(dialog.matrix.columnCount(), 6)
        self.assertEqual(
            dialog.matrix.verticalHeaderItem(0).text(),
            "Leading",
        )
        self.assertEqual(
            dialog.matrix.horizontalHeaderItem(0).text(),
            "#1",
        )
        self.assertEqual(
            dialog.matrix.verticalHeaderItem(1).text(),
            "Following suit",
        )
        self.assertEqual(
            dialog.matrix.verticalHeaderItem(2).text(),
            "Discarding",
        )

        first_cell = dialog.matrix.cellWidget(0, 0)
        self.assertEqual(
            first_cell.findChild(QLabel, "labelColor").text(),
            "Red",
        )
        self.assertIn(
            "#ef4444",
            first_cell.findChild(QLabel, "labelColor").styleSheet(),
        )
        self.assertEqual(
            first_cell.findChild(QLabel, "ddsBehavior").text(),
            "Override DDS",
        )

        expected_orders = (
            ("RED", "ORANGE", "PURPLE", "BLUE", "GREEN", "YELLOW"),
            ("GREEN", "BLUE", "PURPLE", "ORANGE", "RED", "YELLOW"),
            ("BLUE", "PURPLE", "ORANGE", "RED", "GREEN", "YELLOW"),
        )
        for row, expected_order in enumerate(expected_orders):
            self.assertEqual(
                tuple(
                    dialog.matrix.cellWidget(row, column)
                    .findChild(QLabel, "labelColor")
                    .text()
                    .upper()
                    for column in range(dialog.matrix.columnCount())
                ),
                expected_order,
            )

        orange_column = expected_orders[0].index("ORANGE")
        orange_cell = dialog.matrix.cellWidget(0, orange_column)
        self.assertEqual(
            orange_cell.findChild(QLabel, "ddsBehavior").text(),
            "Follow DDS",
        )

    def test_definition_view_translates_label_name_and_dds_behavior(self):
        dialog = LabelDefinitionDialog(language="zh")
        self.addCleanup(dialog.close)

        self.assertEqual(dialog.windowTitle(), "标签.md")
        first_cell = dialog.matrix.cellWidget(0, 0)
        self.assertEqual(
            first_cell.findChild(QLabel, "labelColor").text(),
            "红色",
        )
        self.assertEqual(
            first_cell.findChild(QLabel, "ddsBehavior").text(),
            "覆盖 DDS",
        )
        follow_cell = dialog.matrix.cellWidget(0, 1)
        self.assertEqual(
            follow_cell.findChild(QLabel, "ddsBehavior").text(),
            "遵循 DDS",
        )
