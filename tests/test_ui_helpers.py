import unittest

from src.ui.dialogs.board_editor import BoardEditorDialog


NORTH_EAST_SOUTH_WEST = (
    "N:AKQJ.T98.765.432 432.AKQJ.T98.765 "
    "T98.765.AKQJ.T98 765.432.432.AKQJ"
)


class TestBoardEditorDealParsing(unittest.TestCase):
    def test_parses_standard_single_line_pbn_deal(self):
        hands = BoardEditorDialog._parse_complete_deal(NORTH_EAST_SOUTH_WEST)

        self.assertEqual(hands["NORTH"], "AKQJ.T98.765.432")
        self.assertEqual(hands["EAST"], "432.AKQJ.T98.765")
        self.assertEqual(hands["SOUTH"], "T98.765.AKQJ.T98")
        self.assertEqual(hands["WEST"], "765.432.432.AKQJ")

    def test_parses_direction_prefixed_hands(self):
        deal = "\n".join(
            [
                "N:AKQJ.T98.765.432",
                "E:432.AKQJ.T98.765",
                "S:T98.765.AKQJ.T98",
                "W:765.432.432.AKQJ",
            ]
        )

        self.assertEqual(
            BoardEditorDialog._parse_complete_deal(deal),
            BoardEditorDialog._parse_complete_deal(NORTH_EAST_SOUTH_WEST),
        )

    def test_rejects_incomplete_and_duplicate_deals(self):
        with self.assertRaisesRegex(ValueError, "four PBN hands"):
            BoardEditorDialog._parse_complete_deal("N:AKQJ.T98.765.432")

        duplicate_deal = (
            "N:AKQJ.T98.765.432 AKQJ.T98.765.432 "
            "T98.765.AKQJ.T98 765.432.432.AKQJ"
        )
        with self.assertRaisesRegex(ValueError, "52 unique cards"):
            BoardEditorDialog._parse_complete_deal(duplicate_deal)


if __name__ == "__main__":
    unittest.main()
