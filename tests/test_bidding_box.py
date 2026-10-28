import unittest

from PyQt6.QtWidgets import QApplication

from src.ui.widgets.bidding_box import BiddingBoxDialog


class TestBiddingBoxDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_settings_dialog_has_room_for_auction_and_compact_bid_matrix(self):
        dialog = BiddingBoxDialog()
        self.addCleanup(dialog.close)

        self.assertGreaterEqual(dialog.width(), 720)
        self.assertGreaterEqual(dialog.height(), 620)
        self.assertGreaterEqual(dialog.auction_table.minimumHeight(), 230)
        self.assertEqual(dialog.call_buttons["1NT"].size().width(), 70)
        self.assertEqual(dialog.call_buttons["1NT"].size().height(), 36)

    def test_undo_last_call_clears_the_cell_and_allows_the_call_again(self):
        dialog = BiddingBoxDialog(["1NT", "PASS", "PASS", "PASS"])
        self.addCleanup(dialog.close)

        dialog.undo_call()

        self.assertEqual(
            dialog.bidding_history,
            ["1NT", "PASS", "PASS"],
        )
        self.assertIsNone(dialog.auction_table.item(0, 3))
        self.assertTrue(dialog.special_buttons["PASS"].isEnabled())

        dialog.add_call("PASS")

        self.assertEqual(
            dialog.bidding_history,
            ["1NT", "PASS", "PASS", "PASS"],
        )
        self.assertEqual(dialog.auction_table.item(0, 3).text(), "PASS")


if __name__ == "__main__":
    unittest.main()
