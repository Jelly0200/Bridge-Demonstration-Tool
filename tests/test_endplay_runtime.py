import importlib.util
import unittest

from config.constants import RANKS, SUITS
from src.core.dds_wrapper import DdsWrapper


ENDPLAY_AVAILABLE = importlib.util.find_spec("endplay") is not None
TEST_DEAL = (
    "N:QJ8.AJ965.K82.AQ "
    "43.QT87.QT64.754 "
    "AKT9..A97.J98632 "
    "7652.K432.J53.KT"
)


@unittest.skipUnless(
    ENDPLAY_AVAILABLE,
    "Install the optional Endplay dependency to run native integration tests.",
)
class TestEndplayRuntime(unittest.TestCase):
    def setUp(self):
        self.dds = DdsWrapper("endplay")

    def test_wrapper_calculates_the_documented_dd_table(self):
        result = self.dds.calc_dd_table_pbn(TEST_DEAL)

        if not isinstance(result, dict):
            self.fail("Endplay did not return a double-dummy table.")
        table = result["res_table"]
        self.assertEqual(len(table), 5)
        self.assertTrue(all(len(row) == 4 for row in table))
        self.assertTrue(
            all(0 <= tricks <= 13 for row in table for tricks in row)
        )
        self.assertEqual(table[3][2], 13)

    def test_default_solve_mode_returns_all_cards_with_scores(self):
        result = self.dds.solve_board_pbn(
            TEST_DEAL,
            trump=3,
            first=0,
            solutions=3,
        )

        if not isinstance(result, dict):
            self.fail("Endplay did not return a board solution.")
        self.assertEqual(result["cards"], 13)
        self.assertEqual(len(result["suit"]), 13)
        self.assertEqual(len(result["rank"]), 13)
        self.assertEqual(len(result["score"]), 13)
        self.assertTrue(all(0 <= score <= 13 for score in result["score"]))
        cards = {
            f"{SUITS[suit]}{RANKS[rank - 2]}"
            for suit, rank in zip(result["suit"], result["rank"])
        }
        self.assertEqual(
            cards,
            {
                "SQ", "SJ", "S8", "HA", "HJ", "H9", "H6", "H5",
                "DK", "D8", "D2", "CA", "CQ",
            },
        )

    def test_default_solve_mode_handles_an_existing_trick(self):
        remaining_hands = (
            "J8.AJ965.K82.AQ",
            "4.QT87.QT64.754",
            "AKT9..A97.J98632",
            "7652.K432.J53.KT",
        )
        result = self.dds.solve_board_pbn(
            "N:" + " ".join(remaining_hands),
            trump=3,
            first=0,
            solutions=3,
            current_trick_suit=(0, 0, 0),
            current_trick_rank=(12, 3, 0),
        )

        if not isinstance(result, dict):
            self.fail("Endplay did not solve the position with a current trick.")
        self.assertEqual(result["cards"], 4)
        self.assertTrue(all(0 <= score <= 13 for score in result["score"]))
        cards = {
            f"{SUITS[suit]}{RANKS[rank - 2]}"
            for suit, rank in zip(result["suit"], result["rank"])
        }
        self.assertEqual(cards, {"SA", "SK", "ST", "S9"})


if __name__ == "__main__":
    unittest.main()
