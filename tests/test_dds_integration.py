import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.core import dds_wrapper
from src.core.dds_wrapper import DdsWrapper


class TestDdsWrapper(unittest.TestCase):
    def test_unavailable_solver_raises_clear_errors(self):
        with patch.object(dds_wrapper, "DDS_WHEEL_AVAILABLE", False):
            solver = DdsWrapper()

        self.assertFalse(solver.is_available())
        with self.assertRaisesRegex(RuntimeError, "dds3 module is unavailable"):
            solver.calc_dd_table_pbn("N:...")
        with self.assertRaisesRegex(RuntimeError, "dds3 module is unavailable"):
            solver.solve_board_pbn("N:...")

    def test_solver_methods_delegate_to_dds3(self):
        table_result = {"res_table": [[7, 8, 9, 10]] * 5}
        board_result = SimpleNamespace(cards=["SA", "SK"])
        fake_dds = SimpleNamespace(
            calc_all_tables_pbn=Mock(
                return_value={
                    "no_of_boards": 1,
                    "tables": [table_result],
                    "par_results": [],
                }
            ),
            solve_board_pbn=Mock(return_value=board_result),
        )

        with (
            patch.object(dds_wrapper, "DDS_WHEEL_AVAILABLE", True),
            patch.object(dds_wrapper, "dds3", fake_dds, create=True),
        ):
            solver = DdsWrapper()
            self.assertEqual(solver.calc_dd_table_pbn("N:deal"), table_result)
            self.assertIs(solver.solve_board_pbn("N:deal"), board_result)

        fake_dds.calc_all_tables_pbn.assert_called_once_with(["N:deal"], mode=-1)
        fake_dds.solve_board_pbn.assert_called_once_with(
            "N:deal",
            trump=4,
            first=0,
            current_trick_suit=(0, 0, 0),
            current_trick_rank=(0, 0, 0),
            target=-1,
            solutions=2,
            mode=0,
        )

    def test_solver_errors_return_none(self):
        fake_dds = SimpleNamespace(
            calc_all_tables_pbn=Mock(side_effect=ValueError("bad deal")),
            solve_board_pbn=Mock(side_effect=ValueError("bad deal")),
        )

        with (
            patch.object(dds_wrapper, "DDS_WHEEL_AVAILABLE", True),
            patch.object(dds_wrapper, "dds3", fake_dds, create=True),
        ):
            solver = DdsWrapper()
            self.assertIsNone(solver.calc_dd_table_pbn("N:bad"))
            self.assertIsNone(solver.solve_board_pbn("N:bad"))


if __name__ == "__main__":
    unittest.main()