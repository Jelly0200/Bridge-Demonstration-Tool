import unittest

from PyQt6.QtWidgets import QApplication

from src.robot.label_evaluator import DEFAULT_COLOR_JOBS, LabelEvaluator
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

    def test_definition_view_lists_color_jobs_in_selection_priority_order(self):
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
            "Red",
        )
        leading_rows = [
            (priority, color, job)
            for phase, priority, color, job in dialog.sequence_rows
            if phase == "leading"
        ]
        self.assertEqual(
            leading_rows,
            [
                (priority, color, DEFAULT_COLOR_JOBS["leading"][color])
                for priority, color in enumerate(
                    LabelEvaluator.COLOR_PRIORITY["leading"],
                    start=1,
                )
            ],
        )
        first_color = LabelEvaluator.COLOR_PRIORITY["leading"][0]
        first_cell = dialog.matrix.item(
            0,
            LabelJobsDialog.COLORS.index(first_color),
        )
        self.assertTrue(first_cell.text().startswith("1. "))
