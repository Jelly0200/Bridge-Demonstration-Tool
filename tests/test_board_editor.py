import os
import tempfile
import unittest
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication

from src.core.pbn_parser import PbnParser
from src.database.db_manager import DatabaseManager
from src.database.repository import Repository
from src.ui.dialogs.board_editor import BoardEditorDialog


HANDS = {
    "SOUTH": "T98.765.AKQJ.T98",
    "WEST": "765.432.432.AKQJ",
    "NORTH": "AKQJ.T98.765.432",
    "EAST": "432.AKQJ.T98.765",
}


class TestBoardEditor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        DatabaseManager._instance = None
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        DatabaseManager(os.path.join(self.temp_dir.name, "board_editor.db"))
        self.repo = Repository()
        admin_id = self.repo.create_admin("teacher", "teaching password")
        folder_id = self.repo.create_folder(admin_id, None, "Lessons")
        self.case_id = self.repo.create_case(folder_id, "Opening leads")

    def tearDown(self):
        DatabaseManager._instance = None

    def test_pbn_form_requires_a_valid_complete_deal(self):
        dialog = BoardEditorDialog(case_id=self.case_id)
        self.addCleanup(dialog.close)
        self.assertEqual(set(dialog.pbn_inputs), set(HANDS))
        self.assertFalse(dialog.btn_save.isEnabled())

        for seat, hand in HANDS.items():
            dialog.pbn_inputs[seat].setText(hand)

        self.assertTrue(dialog.btn_save.isEnabled())
        self.assertIn("Valid deal", dialog.pbn_validation_label.text())
        self.assertTrue(
            all(
                len(preview.cards) == 13
                for preview in dialog.pbn_hand_previews.values()
            )
        )

    def test_pbn_form_rejects_duplicate_cards_after_all_52_are_entered(self):
        dialog = BoardEditorDialog(case_id=self.case_id)
        self.addCleanup(dialog.close)
        invalid_hands = {
            "SOUTH": "T98.765.AKQJ.T98",
            "WEST": "765.432.432.AKQJ",
            "NORTH": "AKQJ.T98.765.432",
            "EAST": "AKQJ.T98.765.432",
        }
        for seat, hand in invalid_hands.items():
            dialog.pbn_inputs[seat].setText(hand)

        self.assertFalse(dialog.btn_save.isEnabled())
        self.assertIn("52 unique cards", dialog.pbn_validation_label.text())

    def test_visual_picker_assigns_and_saves_all_52_cards(self):
        dialog = BoardEditorDialog(case_id=self.case_id)
        self.addCleanup(dialog.close)
        dialog.tabs.setCurrentIndex(1)

        for seat, hand in HANDS.items():
            dialog.selected_seat_combo.setCurrentText(seat)
            for suit, ranks in PbnParser.parse_hand(hand).items():
                for rank in ranks:
                    dialog.card_buttons[f"{suit}{rank}"].click()

        self.assertTrue(dialog._picker_is_valid())
        self.assertTrue(dialog.btn_save.isEnabled())

        with patch("src.ui.dialogs.board_editor.QMessageBox.information"):
            dialog.save_board()

        board = self.repo.get_board_by_id(dialog.saved_board_id)
        self.assertIsNotNone(board)
        self.assertEqual(board.case_id, self.case_id)
        self.assertEqual(
            {
                "SOUTH": board.south_hand_pbn,
                "WEST": board.west_hand_pbn,
                "NORTH": board.north_hand_pbn,
                "EAST": board.east_hand_pbn,
            },
            HANDS,
        )

    def test_randomize_deals_remaining_cards_to_empty_seats(self):
        dialog = BoardEditorDialog(case_id=self.case_id)
        self.addCleanup(dialog.close)
        dialog.tabs.setCurrentIndex(1)

        self.assertTrue(dialog.btn_randomize.isEnabled())
        self.assertTrue(dialog._randomize_remaining_cards())
        self.assertTrue(dialog._picker_is_valid())
        self.assertFalse(dialog.btn_randomize.isEnabled())
        self.assertEqual(len(dialog.card_assignments), 52)
        self.assertEqual(
            {
                seat: sum(
                    assigned_seat == seat
                    for assigned_seat in dialog.card_assignments.values()
                )
                for seat in dialog.SEATS
            },
            {seat: 13 for seat in dialog.SEATS},
        )

    def test_randomize_requires_each_seat_to_have_zero_or_thirteen_cards(self):
        dialog = BoardEditorDialog(case_id=self.case_id)
        self.addCleanup(dialog.close)
        dialog.tabs.setCurrentIndex(1)
        dialog.card_assignments["SA"] = "SOUTH"
        dialog._refresh_picker_buttons()

        self.assertFalse(dialog.btn_randomize.isEnabled())
        self.assertFalse(dialog._randomize_remaining_cards())
        self.assertEqual(dialog.card_assignments, {"SA": "SOUTH"})

    def test_picker_shows_a_color_badge_for_each_seat(self):
        dialog = BoardEditorDialog(case_id=self.case_id)
        self.addCleanup(dialog.close)

        self.assertEqual(
            set(dialog.seat_color_legend),
            set(dialog.SEATS),
        )
        for seat, badge in dialog.seat_color_legend.items():
            self.assertIn(seat, badge.text())
            self.assertIn(dialog.SEAT_COLORS[seat], badge.styleSheet())

    def test_randomize_preserves_complete_hands_and_deals_only_empty_seats(self):
        dialog = BoardEditorDialog(case_id=self.case_id)
        self.addCleanup(dialog.close)
        dialog.tabs.setCurrentIndex(1)
        south_cards = [
            f"{suit}{rank}"
            for suit, ranks in PbnParser.parse_hand(HANDS["SOUTH"]).items()
            for rank in ranks
        ]
        dialog.card_assignments.update(
            {card: "SOUTH" for card in south_cards}
        )
        dialog._refresh_picker_buttons()

        self.assertTrue(dialog.btn_randomize.isEnabled())
        self.assertTrue(dialog._randomize_remaining_cards())
        self.assertTrue(
            all(dialog.card_assignments[card] == "SOUTH" for card in south_cards)
        )
        self.assertTrue(dialog._picker_is_valid())

    def test_editing_selected_board_updates_its_saved_deal(self):
        board_id = self.repo.save_board(
            case_id=self.case_id,
            hands=HANDS,
            dealer="SOUTH",
            vulnerability="NONE",
        )
        dialog = BoardEditorDialog(board_id=board_id)
        self.addCleanup(dialog.close)
        self.assertTrue(dialog.btn_save.isEnabled())
        dialog.dealer_combo.setCurrentText("WEST")
        dialog.description_input.setText("Updated lesson")

        with patch("src.ui.dialogs.board_editor.QMessageBox.information"):
            dialog.save_board()

        updated = self.repo.get_board_by_id(board_id)
        configuration = self.repo.get_board_configuration(
            updated.board_configuration_id
        )
        self.assertEqual(configuration.dealer, "WEST")
        self.assertEqual(updated.description, "Updated lesson")


if __name__ == "__main__":
    unittest.main()
