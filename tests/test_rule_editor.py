import unittest

from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QTableWidgetItem

from src.database.models.scenario import Scenario
from src.ui.dialogs.label_color_dialog import LabelColorDialog
from src.ui.dialogs.rule_editor import RuleEditorDialog
from src.ui.widgets.hand_widget import CardWidget


class TestRuleEditorDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_new_scenario_rules_start_with_empty_lists(self):
        dialog = RuleEditorDialog(Scenario(id=1, board_id=1), labels=[])
        self.addCleanup(dialog.close)

        self.assertEqual(dialog.label_table.rowCount(), 0)
        self.assertEqual(dialog.seq_input.text(), "")

        dialog.save_rules()

        self.assertEqual(dialog.saved_labels, [])
        self.assertEqual(dialog.saved_targeted_sequence, "[]")
        self.assertEqual(dialog.result(), dialog.DialogCode.Accepted)

    def test_orange_and_purple_are_valid_label_colors_with_distinct_styles(self):
        dialog = RuleEditorDialog(Scenario(id=1, board_id=1), labels=[])
        self.addCleanup(dialog.close)
        dialog.label_table.setRowCount(2)
        for row, color in enumerate(("ORANGE", "PURPLE")):
            for column, value in enumerate((str(row + 1), color, "SA")):
                dialog.label_table.setItem(
                    row,
                    column,
                    QTableWidgetItem(value),
                )

        self.assertEqual(
            [label["Color"] for label in dialog._validated_labels()],
            ["ORANGE", "PURPLE"],
        )
        self.assertIn("ORANGE", LabelColorDialog.COLORS)
        self.assertIn("PURPLE", LabelColorDialog.COLORS)
        self.assertNotEqual(
            CardWidget.COLOR_MAP["ORANGE"],
            CardWidget.COLOR_MAP["PURPLE"],
        )

    def test_label_color_dialog_shows_six_color_buttons_and_can_clear(self):
        dialog = LabelColorDialog(
            "SA",
            current_color="RED",
            current_sequence=4,
            sequence_counts={"RED": 4, "BLUE": 2, "PURPLE": 1},
        )
        self.addCleanup(dialog.close)
        dialog.show()
        self.application.processEvents()

        self.assertEqual(
            tuple(dialog.color_buttons),
            ("RED", "ORANGE", "YELLOW", "BLUE", "PURPLE", "GREEN"),
        )
        self.assertGreaterEqual(dialog.width(), 800)
        self.assertLessEqual(
            max(
                button.geometry().right()
                for button in dialog.color_buttons.values()
            ),
            dialog.color_bar.width(),
        )
        self.assertTrue(dialog.color_buttons["RED"].isChecked())

        dialog.color_buttons["PURPLE"].click()
        self.assertEqual(dialog.selected_color, "PURPLE")
        self.assertEqual(dialog.sequence_spin.value(), 1)
        self.assertIn("inset", dialog.color_buttons["PURPLE"].styleSheet())
        dialog.color_buttons["RED"].click()
        self.assertEqual(dialog.sequence_spin.value(), 4)
        dialog.color_buttons["BLUE"].click()
        self.assertEqual(dialog.sequence_spin.value(), 2)
        dialog.btn_clear.click()
        self.assertEqual(dialog.selected_color, "NONE")
        self.assertFalse(
            any(button.isChecked() for button in dialog.color_buttons.values())
        )


if __name__ == "__main__":
    unittest.main()
