import unittest
from unittest.mock import Mock, patch

from PyQt6.QtWidgets import QApplication

from src.database.models.scenario import Scenario
from src.ui.dialogs.scenario_editor import ScenarioEditorDialog


class TestScenarioEditorDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_scenario_risk_status_is_derived_from_the_route(self):
        scenario = Scenario(
            id=3,
            board_id=1,
            bidding_route="1S DBL PASS PASS PASS",
            risk_status="REDOUBLE",
        )
        repository = Mock()
        with patch(
            "src.ui.dialogs.scenario_editor.Repository",
            return_value=repository,
        ):
            dialog = ScenarioEditorDialog(1, scenario)
        self.addCleanup(dialog.close)

        self.assertFalse(hasattr(dialog, "risk_combo"))
        dialog.bidding_route_input.setText(
            "1S DBL PASS RDBL PASS PASS"
        )
        dialog.save_scenario()

        self.assertEqual(repository.update_scenario.call_args.args[4], "REDOUBLE")
        self.assertEqual(dialog.result(), dialog.DialogCode.Accepted)


if __name__ == "__main__":
    unittest.main()
