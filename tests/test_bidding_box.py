import unittest

from PyQt6.QtWidgets import QApplication

from src.core.bridge_logic import BridgeLogic
from src.ui.widgets.bidding_box import BiddingBoxDialog


class TestBiddingBoxDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_bidding_route_and_bid_matrix_are_centered_and_compact(self):
        dialog = BiddingBoxDialog()
        self.addCleanup(dialog.close)

        self.assertGreaterEqual(dialog.width(), 560)
        self.assertLess(dialog.height(), 620)
        self.assertLess(dialog.auction_table.minimumHeight(), 50)
        self.assertEqual(dialog.auction_table.width(), 560)
        self.assertEqual(dialog.call_buttons["1NT"].size().width(), 76)
        self.assertEqual(dialog.call_buttons["1NT"].size().height(), 36)
        self.assertFalse(hasattr(dialog, "information_editor"))
        self.assertFalse(hasattr(dialog, "risk_combo"))
        self.assertEqual(
            dialog.STRAINS,
            (("NT", "NT"), ("♠", "S"), ("♥", "H"), ("♦", "D"), ("♣", "C")),
        )
        self.assertEqual(
            [dialog.call_buttons[f"{level}NT"].text() for level in "1234567"],
            [f"{level}NT" for level in "1234567"],
        )

        dialog.show()
        self.application.processEvents()
        self.assertEqual(
            dialog.auction_table.geometry().center().x(),
            dialog.rect().center().x(),
        )
        self.assertEqual(
            dialog.call_matrix.geometry().center().x(),
            dialog.rect().center().x(),
        )

    def test_test_preview_shows_only_a_read_only_bidding_route(self):
        dialog = BiddingBoxDialog(
            ["1NT", "PASS", "PASS", "PASS"],
            read_only=True,
            route_only=True,
        )
        self.addCleanup(dialog.close)

        dialog.show()
        self.application.processEvents()

        self.assertEqual(dialog.auction_label.text(), "Bidding route")
        self.assertFalse(dialog.call_matrix.isVisible())
        self.assertFalse(dialog.special_controls.isVisible())
        self.assertFalse(dialog.btn_save.isVisible())
        self.assertTrue(dialog.btn_cancel.isVisible())
        self.assertEqual(dialog.bidding_history[-1], "PASS")

    def test_strain_colors_are_used_in_the_matrix_and_bidding_route(self):
        dialog = BiddingBoxDialog(["1NT", "2S"])
        self.addCleanup(dialog.close)

        self.assertEqual(dialog.STRAIN_COLORS["NT"], "#9ca3af")
        self.assertEqual(dialog.STRAIN_COLORS["S"], "#3b82f6")
        self.assertIn(
            f"color: {dialog.STRAIN_COLORS['NT']}",
            dialog.call_buttons["1NT"].styleSheet(),
        )
        self.assertIn(
            f"color: {dialog.STRAIN_COLORS['S']}",
            dialog.call_buttons["1S"].styleSheet(),
        )
        self.assertEqual(
            dialog.auction_table.item(0, 0).foreground().color().name(),
            dialog.STRAIN_COLORS["NT"],
        )
        self.assertEqual(
            dialog.auction_table.item(0, 1).foreground().color().name(),
            dialog.STRAIN_COLORS["S"],
        )

    def test_risk_status_is_derived_from_the_auction_route(self):
        self.assertEqual(
            BridgeLogic.derive_risk_status(["1H", "DBL", "PASS"]),
            "DOUBLE",
        )
        self.assertEqual(
            BridgeLogic.derive_risk_status(
                ["1H", "DBL", "PASS", "RDBL", "PASS"]
            ),
            "REDOUBLE",
        )
        self.assertEqual(
            BridgeLogic.derive_risk_status(
                ["1H", "DBL", "PASS", "2H"]
            ),
            "NONE",
        )

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
        self.assertEqual(dialog.risk_status, "NONE")


if __name__ == "__main__":
    unittest.main()
