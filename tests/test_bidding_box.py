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


if __name__ == "__main__":
    unittest.main()
