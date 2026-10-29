import unittest
from types import SimpleNamespace
from unittest.mock import patch

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QDialog

from src.database.models.case_board import Board, BoardConfiguration
from src.database.models.scenario import Label, Scenario
from src.ui.views.table_view import TableView
from src.ui.widgets.hand_widget import CardWidget


class FirstLegalRobot:
    def __init__(self, table):
        self.table = table

    def select_move(self, player, labels, current_pbn_deal):
        legal_cards = self.table.game.get_legal_cards(player)
        return legal_cards[0] if legal_cards else None


class TestTableView(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        self.board = Board(
            id=1,
            case_id=1,
            board_configuration_id=1,
            south_hand_pbn="T98.765.AKQJ.T98",
            west_hand_pbn="765.432.432.AKQJ",
            north_hand_pbn="AKQJ.T98.765.432",
            east_hand_pbn="432.AKQJ.T98.765",
            description="Test board",
        )
        self.configuration = BoardConfiguration(
            id=1,
            dealer="SOUTH",
            vulnerability="NONE",
        )
        self.table = TableView()
        self.addCleanup(self.table.close)

    def test_loads_board_hands_and_contract_from_scenario(self):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="1NT PASS PASS PASS",
            declarer="SOUTH",
            contract="1NT",
        )

        self.table.load_board(
            self.board,
            self.configuration,
            scenario,
            [Label(sequence=1, color="RED", card="AH")],
        )

        self.assertEqual(len(self.table.hand_widgets["SOUTH"].cards), 13)
        self.assertEqual(len(self.table.hand_widgets["WEST"].cards), 13)
        self.assertEqual(self.table.game.contract, "1NT")
        self.assertEqual(self.table.game.current_player, "WEST")
        self.assertIn("1NT NONE", self.table.center_info.text())
        self.assertNotIn("Test board", self.table.center_info.text())
        self.assertEqual(self.table.btn_demonstration.text(), "Demonstrate")
        self.assertTrue(self.table.btn_demonstration.isEnabled())

    def test_all_hands_use_the_same_card_size(self):
        self.table.load_board(self.board, self.configuration)

        west_hand = self.table.hand_widgets["WEST"]
        self.assertFalse(west_hand.horizontal)
        self.assertEqual(west_hand.main_layout.count(), 4)
        self.assertTrue(all(not card.compact for card in west_hand.cards))
        self.assertTrue(
            all((card.width(), card.height()) == (44, 62) for card in west_hand.cards)
        )

        north_hand = self.table.hand_widgets["NORTH"]
        self.assertTrue(north_hand.horizontal)
        self.assertEqual(north_hand.main_layout.count(), 1)
        self.assertTrue(
            all((card.width(), card.height()) == (44, 62) for card in north_hand.cards)
        )

    def test_dds_card_values_have_enough_height_for_their_font(self):
        for compact in (False, True):
            with self.subTest(compact=compact):
                card = CardWidget("SA", compact=compact)
                card.set_dds_tricks(13)

                self.assertFalse(card.dds_label.isHidden())
                self.assertEqual(card.dds_label.text(), "13")
                self.assertGreaterEqual(
                    card.dds_label.height(),
                    QFontMetrics(card.dds_label.font()).height() + 4,
                )

    def test_playing_a_card_reuses_widgets_for_cards_still_in_each_hand(self):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="1NT PASS PASS PASS",
            declarer="SOUTH",
            contract="1NT",
        )
        self.table.load_board(self.board, self.configuration, scenario)
        retained_widgets = {
            (seat, card.card_code): card
            for seat, hand in self.table.hand_widgets.items()
            for card in hand.cards
            if not (seat == "WEST" and card.card_code == "S7")
        }

        self.table.on_card_selected("WEST", "S7")

        self.assertNotIn(
            "S7",
            {
                card.card_code
                for card in self.table.hand_widgets["WEST"].cards
            },
        )
        for (seat, card_code), widget in retained_widgets.items():
            current_widget = next(
                card
                for card in self.table.hand_widgets[seat].cards
                if card.card_code == card_code
            )
            self.assertIs(current_widget, widget)

    def test_played_card_widgets_are_reused_in_a_centered_trick_area(self):
        game = SimpleNamespace(
            current_trick=[("SOUTH", "S2")],
            completed_tricks=[],
        )
        self.table.game = game
        self.table.show()
        self.application.processEvents()

        for card_code in ("S2", "S3", "S4", "S5"):
            game.current_trick = [("SOUTH", card_code)]
            self.table._render_played_cards()

        widgets = self.table.played_card_area.findChildren(CardWidget)
        self.assertEqual(len(widgets), 1)
        self.assertIs(widgets[0], self.table.played_card_widgets["SOUTH"])
        self.assertEqual(widgets[0].card_code, "S5")
        self.assertEqual(
            self.table.played_cards_grid.getItemPosition(
                self.table.played_cards_grid.indexOf(widgets[0])
            )[:2],
            (2, 1),
        )
        game.current_trick = [
            ("SOUTH", "S2"),
            ("WEST", "H2"),
            ("NORTH", "D2"),
            ("EAST", "C2"),
        ]
        self.table._render_played_cards()
        expected_positions = {
            "SOUTH": (2, 1),
            "WEST": (1, 0),
            "NORTH": (0, 1),
            "EAST": (1, 2),
        }
        self.assertEqual(
            {
                seat: self.table.played_cards_grid.getItemPosition(
                    self.table.played_cards_grid.indexOf(widget)
                )[:2]
                for seat, widget in self.table.played_card_widgets.items()
            },
            expected_positions,
        )
        center = self.table.played_card_area.rect().center()
        card_centers = {
            seat: widget.mapTo(
                self.table.played_card_area,
                widget.rect().center(),
            )
            for seat, widget in self.table.played_card_widgets.items()
        }
        self.assertEqual(card_centers["NORTH"].x(), center.x())
        self.assertEqual(card_centers["SOUTH"].x(), center.x())
        self.assertEqual(card_centers["WEST"].y(), center.y())
        self.assertEqual(card_centers["EAST"].y(), center.y())
        self.table.trick_grid.activate()
        area_center = self.table.played_card_area.geometry().center()
        table_center = self.table.trick_area.rect().center()
        self.assertLessEqual(abs(area_center.x() - table_center.x()), 1)
        self.assertLessEqual(abs(area_center.y() - table_center.y()), 1)

    def test_played_card_widget_reuse_preserves_each_suit_color(self):
        self.table.game = SimpleNamespace(
            current_trick=[("SOUTH", "H2")],
            completed_tricks=[],
        )
        self.table._render_played_cards()
        widget = self.table.played_card_widgets["SOUTH"]

        self.table.game.current_trick = [("SOUTH", "S3")]
        self.table._render_played_cards()

        self.assertIs(self.table.played_card_widgets["SOUTH"], widget)
        self.assertEqual(
            widget.rank_label.styleSheet(),
            "color: #1a1a1a; background: transparent;",
        )
        self.assertEqual(
            widget.card_label.styleSheet(),
            "color: #1a1a1a; background: transparent;",
        )

    def test_robot_card_sound_can_be_toggled(self):
        with patch("src.ui.views.table_view.QSoundEffect.play") as play:
            self.table._play_robot_card_sound()
            play.assert_called_once()

            self.table.set_robot_card_sound_enabled(False)
            self.table._play_robot_card_sound()

        play.assert_called_once()

    def test_board_only_center_shows_a_prompt_instead_of_board_details(self):
        self.table.load_board(self.board, self.configuration)

        center_text = self.table.center_info.text()
        self.assertIn("Double-click a scenario", center_text)
        self.assertNotIn("Test board", center_text)
        self.assertNotIn("Dealer:", center_text)
        self.assertNotIn("Vulnerability:", center_text)

    def test_record_target_button_is_in_the_top_bar(self):
        self.assertGreaterEqual(
            self.table.top_bar_layout.indexOf(self.table.btn_record),
            0,
        )

    def test_hidden_view_removes_concealed_cards_and_restores_them(self):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="1NT PASS PASS PASS",
            declarer="SOUTH",
            contract="1NT",
        )
        self.table.load_board(self.board, self.configuration, scenario)
        self.table.current_side = "SOUTH"
        self.table.current_mode = "DEMONSTRATION"
        self.table.view_mode = "HIDDEN"
        self.table._apply_view_mode()

        for seat in ("EAST", "WEST"):
            self.assertTrue(
                all(card.isHidden() for card in self.table.hand_widgets[seat].cards)
            )
        for seat in ("NORTH", "SOUTH"):
            self.assertTrue(
                all(not card.isHidden() for card in self.table.hand_widgets[seat].cards)
            )

        self.table.view_mode = "ANALYSIS"
        self.table._apply_view_mode()
        self.assertTrue(
            all(
                not card.isHidden()
                for hand in self.table.hand_widgets.values()
                for card in hand.cards
            )
        )

    def test_lockdown_keeps_only_settings_and_move_navigation_controls(self):
        self.table.set_lockdown_mode(True)

        self.assertFalse(self.table.btn_settings.isHidden())
        self.assertFalse(self.table.btn_prev.isHidden())
        self.assertFalse(self.table.btn_next.isHidden())
        self.assertTrue(self.table.btn_view_mode.isHidden())
        self.assertTrue(self.table.btn_toggle_dds_matrix.isHidden())
        self.assertTrue(self.table.dds_result_table.isHidden())

        self.table.set_lockdown_mode(False)
        self.assertFalse(self.table.btn_view_mode.isHidden())

    def test_dds_matrix_is_flush_with_the_view_and_footer_layout_edges(self):
        self.table.show()
        self.application.processEvents()

        matrix_rect = self.table.dds_result_table.geometry()
        footer_item_rect = self.table.footer_layout.itemAt(4).geometry()
        self.assertEqual(matrix_rect.right() + 1, self.table.width())
        self.assertEqual(matrix_rect.bottom() + 1, footer_item_rect.bottom() + 1)

    def test_empty_scenario_keeps_play_features_disabled(self):
        scenario = Scenario(id=1, board_id=1)
        self.table.load_board(self.board, self.configuration, scenario)

        self.assertEqual(self.table.bidding_route, [])
        self.assertEqual(self.table.labels, [])
        self.assertEqual(self.table.target_sequence, [])
        self.assertIsNone(self.table.robot)
        self.assertFalse(self.table.is_scenario_ready())
        self.assertIsNone(self.table.game.contract)
        self.assertIn("complete, legal auction", self.table.center_info.text())

    def test_label_mode_is_ready_without_labels_and_creates_a_robot(self):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="1NT PASS PASS PASS",
            declarer="SOUTH",
            contract="1NT",
        )
        self.table.load_board(self.board, self.configuration, scenario)

        self.assertTrue(self.table.is_scenario_ready())
        self.assertIsNotNone(self.table.robot)
        self.assertEqual(self.table.btn_mode.text(), "Mode: Normal")
        self.assertFalse(self.table.btn_mode.isEnabled())
        self.table.btn_mode.click()
        self.assertEqual(self.table.current_mode, "NORMAL")
        emitted_modes = []
        self.table.mode_changed.connect(emitted_modes.append)

        self.table.btn_demonstration.click()
        QTest.qWait(self.table.ROBOT_MOVE_DELAY_MS + 60)

        self.assertEqual(self.table.current_mode, "DEMONSTRATION")
        self.assertEqual(self.table.btn_demonstration.text(), "Stop")
        self.assertTrue(self.table.btn_demonstration.isEnabled())
        self.assertEqual(emitted_modes, ["DEMONSTRATION"])
        self.assertFalse(self.table.btn_side.isEnabled())
        self.assertFalse(self.table.btn_rotate.isEnabled())
        self.assertFalse(self.table.btn_dds_display.isEnabled())
        self.assertTrue(self.table.btn_view_mode.isEnabled())
        locked_side = self.table.current_side
        locked_perspective = self.table.perspective
        locked_dds_mode = self.table.dds_display_mode
        self.table.btn_side.click()
        self.table.btn_rotate.click()
        self.table.btn_dds_display.click()
        self.table.select_side()
        self.table.rotate_perspective()
        self.table.toggle_dds_display_mode()
        self.assertEqual(self.table.current_side, locked_side)
        self.assertEqual(self.table.perspective, locked_perspective)
        self.assertEqual(self.table.dds_display_mode, locked_dds_mode)
        self.table.btn_view_mode.click()
        self.assertEqual(self.table.view_mode, "HIDDEN")
        self.table.btn_view_mode.click()
        self.assertEqual(self.table.view_mode, "ANALYSIS")
        self.assertEqual(self.table.game.current_player, "NORTH")
        self.assertEqual(set(self.table.played_card_widgets), {"WEST"})
        self.assertTrue(self.table.dds_result_table.isHidden())
        self.assertTrue(
            all(
                card.dds_tricks is None
                for hand in self.table.hand_widgets.values()
                for card in hand.cards
            )
        )

        self.table.set_mode("NORMAL")
        self.assertFalse(self.table.dds_result_table.isHidden())
        self.assertTrue(self.table.btn_side.isEnabled())
        self.assertTrue(self.table.btn_rotate.isEnabled())
        self.assertTrue(self.table.btn_dds_display.isEnabled())

    def test_demonstration_button_ends_demonstration(self):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="1NT PASS PASS PASS",
            declarer="SOUTH",
            contract="1NT",
        )
        self.table.load_board(self.board, self.configuration, scenario)

        self.table.btn_demonstration.click()
        self.assertEqual(self.table.current_mode, "DEMONSTRATION")
        self.assertEqual(self.table.btn_demonstration.text(), "Stop")

        self.table.btn_demonstration.click()
        self.assertEqual(self.table.current_mode, "NORMAL")
        self.assertEqual(self.table.btn_demonstration.text(), "Demonstrate")
        self.assertTrue(self.table.btn_side.isEnabled())
        self.assertTrue(self.table.btn_dds_display.isEnabled())

    def test_restarting_demonstration_rebuilds_clean_game_and_robot_state(self):
        self._prepare_robot_demonstration("SOUTH")
        previous_game = self.table.game
        self.assertTrue(self.table.move_history)
        self.table.labels = [
            {"Sequence": 1, "Color": "RED", "Card": "S7"}
        ]

        self.table.set_mode("NORMAL")
        self.assertFalse(self.table.robot_timer.isActive())
        self.table.start_demonstration()

        self.assertIsNot(self.table.game, previous_game)
        self.assertEqual(self.table.game.current_trick, [])
        self.assertEqual(self.table.move_history, [])
        self.assertIs(self.table.robot.game, self.table.game)
        self.assertTrue(self.table.robot_timer.isActive())
        QTest.qWait(self.table.ROBOT_MOVE_DELAY_MS + 60)
        self.assertTrue(self.table.move_history)
        self.assertEqual(self.table.game.current_trick[0], ("WEST", "S7"))

    def test_normal_mode_allows_manual_play_from_any_seat(self):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="1NT PASS PASS PASS",
            declarer="SOUTH",
            contract="1NT",
        )
        self.table.load_board(self.board, self.configuration, scenario)

        self.table.on_card_selected("WEST", "S7")

        self.assertEqual(self.table.game.current_player, "NORTH")
        self.assertNotIn("robot controls", self.table.center_info.text().lower())

    def test_normal_mode_does_not_activate_robot_when_human_seat_changes(self):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="1NT PASS PASS PASS",
            declarer="SOUTH",
            contract="1NT",
        )
        self.table.load_board(self.board, self.configuration, scenario)
        self.table.robot = FirstLegalRobot(self.table)
        self.table.current_side = "NORTH"

        self.table.select_side()

        self.assertEqual(self.table.current_mode, "NORMAL")
        self.assertEqual(self.table.game.current_player, "WEST")
        self.assertEqual(self.table.game.current_trick, [])

    def _prepare_robot_demonstration(self, human_seat):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="1NT PASS PASS PASS",
            declarer="SOUTH",
            contract="1NT",
            is_targeted=1,
            targeted_sequence='["S7"]',
        )
        self.table.load_board(self.board, self.configuration, scenario)
        scenario.is_targeted = 0
        self.table.rule_mode = "LABEL"
        self.table.btn_rule_mode.setText("Rule: Label")
        self.table.current_side = human_seat
        self.table.btn_side.setText(f"Human seat: {human_seat}")
        self.table.robot = FirstLegalRobot(self.table)
        self.assertTrue(self.table.set_mode("DEMONSTRATION"))
        QTest.qWait(self.table.ROBOT_MOVE_DELAY_MS + 60)

    def _wait_for_completed_trick(self):
        for _ in range(400):
            if self.table.game.completed_tricks:
                break
            QTest.qWait(20)
        self.assertTrue(self.table.game.completed_tricks)
        self.table.set_mode("NORMAL")

    def test_demonstration_robot_plays_defenders_while_human_declarer_plays_dummy(self):
        self._prepare_robot_demonstration("SOUTH")

        self.assertEqual(self.table.game.current_player, "NORTH")
        self.assertEqual(
            {seat for seat, _ in self.table.game.current_trick},
            {"WEST"},
        )
        north_card = self.table.game.get_legal_cards("NORTH")[0]
        self.table.on_card_selected("NORTH", north_card)
        QTest.qWait(self.table.ROBOT_MOVE_DELAY_MS + 60)
        self.assertEqual(self.table.game.current_player, "SOUTH")

        south_card = self.table.game.get_legal_cards("SOUTH")[0]
        self.table.on_card_selected("SOUTH", south_card)
        self._wait_for_completed_trick()
        self.assertEqual(len(self.table.game.completed_tricks[0]), 4)

    def test_demonstration_robot_plays_all_seats_except_human_defender(self):
        self._prepare_robot_demonstration("WEST")

        self.assertEqual(self.table.game.current_player, "WEST")
        west_card = self.table.game.get_legal_cards("WEST")[0]
        self.table.on_card_selected("WEST", west_card)
        self._wait_for_completed_trick()

        self.assertEqual(len(self.table.game.completed_tricks), 1)
        self.assertEqual(len(self.table.game.completed_tricks[0]), 4)

    def test_target_playback_can_advance_and_restore_a_card(self):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="1NT PASS PASS PASS",
            declarer="SOUTH",
            contract="1NT",
            is_targeted=1,
            targeted_sequence='["S7", "SA"]',
        )

        self.table.load_board(
            self.board,
            self.configuration,
            scenario,
            [Label(sequence=1, color="RED", card="AH")],
        )
        self.table.set_mode("DEMONSTRATION")
        self.table.start_demonstration()

        self.table.play_next_target_card()
        self.assertEqual(self.table.target_index, 1)
        self.assertEqual(self.table.game.current_player, "NORTH")
        self.assertEqual(len(self.table.hand_widgets["WEST"].cards), 12)

        self.table.play_previous_target_card()
        self.assertEqual(self.table.target_index, 0)
        self.assertEqual(self.table.game.current_player, "WEST")
        self.assertEqual(len(self.table.hand_widgets["WEST"].cards), 13)
        east_cards = {
            card.card_code: card for card in self.table.hand_widgets["EAST"].cards
        }
        self.assertEqual(east_cards["HA"].label_color, "RED")

    def test_hidden_view_faces_down_opponents_for_declarer_human(self):
        self.table.load_board(self.board, self.configuration)
        self.table.toggle_view_mode()

        self.assertTrue(
            all(not hand.isHidden() for hand in self.table.hand_widgets.values())
        )
        self.assertTrue(self.table.dds_result_table.isHidden())

        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="1NT PASS PASS PASS",
            declarer="SOUTH",
            contract="1NT",
        )
        self.table.load_board(self.board, self.configuration, scenario)
        self.assertTrue(self.table.set_mode("DEMONSTRATION"))
        self.table.toggle_view_mode()

        for hand in self.table.hand_widgets.values():
            self.assertFalse(hand.isHidden())
        for seat in ("EAST", "WEST"):
            self.assertTrue(
                all(card.is_hidden for card in self.table.hand_widgets[seat].cards)
            )
        for seat in ("NORTH", "SOUTH"):
            self.assertTrue(
                all(
                    not card.is_hidden
                    for card in self.table.hand_widgets[seat].cards
                )
            )

    def test_hidden_view_for_defender_faces_up_dummy_and_down_other_opponents(self):
        self._prepare_robot_demonstration("WEST")
        self.table.toggle_view_mode()

        for seat in ("NORTH",):
            self.assertTrue(
                all(
                    card.is_hidden
                    for card in self.table.hand_widgets[seat].cards
                )
            )
        for seat in ("WEST",):
            self.assertTrue(
                all(
                    not card.is_hidden
                    for card in self.table.hand_widgets[seat].cards
                )
            )
        for seat in ("EAST", "SOUTH"):
            self.assertTrue(
                all(card.is_hidden for card in self.table.hand_widgets[seat].cards)
            )

        west_card = self.table.game.get_legal_cards("WEST")[0]
        self.table.on_card_selected("WEST", west_card)

        self.assertTrue(
            all(
                not card.is_hidden
                for card in self.table.hand_widgets["NORTH"].cards
            )
        )

    def test_target_recording_flushes_sequence_and_analysis_undo_reverts_moves(self):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="1NT PASS PASS PASS",
            is_targeted=1,
            targeted_sequence='["HA"]',
        )
        self.table.load_board(self.board, self.configuration, scenario)
        self.assertTrue(self.table.btn_record.isEnabled())
        self.assertEqual(self.table.target_sequence, ["HA"])

        self.table.btn_record.click()
        self.assertTrue(self.table.recording_target)
        self.assertEqual(self.table.target_sequence, [])
        self.table.on_card_selected("WEST", "S7")
        self.table.on_card_selected("NORTH", "SA")

        self.assertEqual(self.table.target_sequence, ["S7", "SA"])
        self.table.btn_prev.click()
        self.assertEqual(self.table.target_sequence, ["S7"])
        self.assertEqual(self.table.game.current_player, "NORTH")

        self.table.btn_record.click()
        self.assertFalse(self.table.recording_target)
        self.assertEqual(scenario.targeted_sequence, '["S7"]')

    def test_central_controls_have_two_face_mode_and_rule_labels(self):
        self.assertEqual(self.table.btn_view_mode.text(), "View: Analysis")
        self.assertEqual(self.table.btn_mode.text(), "Mode: Normal")
        self.assertEqual(self.table.btn_rule_mode.text(), "Rule: Label")
        self.assertEqual(self.table.btn_prev.text(), "Last move")
        self.assertEqual(self.table.btn_reset.text(), "Reset")
        self.assertEqual(self.table.btn_next.text(), "Next move")

    def test_language_switch_translates_live_text_but_leaves_dds_controls_unchanged(self):
        self.table.language_controller.set_language("zh")

        self.assertEqual(self.table.btn_settings.text(), "设置")
        self.assertEqual(self.table.btn_view_mode.text(), "视图：分析")
        self.assertEqual(self.table.btn_dds_display.text(), "DDS: Tricks")
        self.assertEqual(self.table.btn_toggle_dds_matrix.text(), "Hide DDS")

        self.table.center_info.setText("Play complete.")
        self.assertEqual(self.table.center_info.text(), "牌局已结束。")

        self.table.language_controller.set_language("en")
        self.assertEqual(self.table.btn_settings.text(), "Settings")
        self.assertEqual(self.table.center_info.text(), "Play complete.")

    def test_card_rank_suit_and_dds_value_fit_inside_the_card(self):
        self.table.load_board(self.board, self.configuration)
        card = next(
            widget
            for widget in self.table.hand_widgets["WEST"].cards
            if widget.card_code == "S7"
        )
        card.set_dds_tricks(6)
        card.layout().activate()
        QApplication.processEvents()

        self.assertEqual(card.rank_label.text(), "7")
        self.assertEqual(card.card_label.text(), "♠")
        self.assertEqual(card.dds_label.text(), "6")
        self.assertEqual(card.rank_label.font().pointSize(), 14)
        self.assertEqual(card.card_label.font().pointSize(), 30)
        self.assertEqual(card.dds_label.font().pointSize(), 7)
        self.assertEqual(card.dds_label.width(), 22)
        self.assertLess(card.rank_label.y(), card.height() // 3)
        self.assertGreater(card.dds_label.y(), card.height() // 2)
        self.assertLessEqual(card.rank_label.geometry().bottom(), card.height())
        self.assertLessEqual(card.card_label.geometry().bottom(), card.height())
        self.assertLessEqual(card.dds_label.geometry().bottom(), card.height())

    def test_label_sequence_appears_in_matching_label_color(self):
        self.table.load_board(self.board, self.configuration)
        card = next(
            widget
            for widget in self.table.hand_widgets["WEST"].cards
            if widget.card_code == "S7"
        )

        card.set_label_color("BLUE")
        card.set_label_sequence(3)
        card.layout().activate()
        QApplication.processEvents()

        self.assertEqual(card.sequence_label.text(), "3")
        self.assertEqual(
            card.sequence_label.font().pointSize(),
            10,
        )
        self.assertGreaterEqual(
            card.sequence_label.height(),
            QFontMetrics(card.sequence_label.font()).height(),
        )
        self.assertEqual(
            card.sequence_label.styleSheet(),
            f"color: {card.COLOR_MAP['BLUE']}; background: transparent;",
        )
        self.assertFalse(card.sequence_label.isHidden())
        self.assertGreaterEqual(card.sequence_label.x(), card.width() // 2)
        self.assertLess(card.sequence_label.y(), card.height() // 3)

    def test_setting_label_sequence_reorders_only_that_color(self):
        self.table.labels = [
            {"Sequence": 1, "Color": "RED", "Card": "S7"},
            {"Sequence": 2, "Color": "RED", "Card": "H7"},
            {"Sequence": 3, "Color": "RED", "Card": "D7"},
            {"Sequence": 1, "Color": "BLUE", "Card": "C7"},
        ]

        self.table._set_card_label("C6", "RED", 2)

        red_labels = sorted(
            (label for label in self.table.labels if label["Color"] == "RED"),
            key=lambda label: label["Sequence"],
        )
        self.assertEqual(
            [(label["Card"], label["Sequence"]) for label in red_labels],
            [("S7", 1), ("C6", 2), ("H7", 3), ("D7", 4)],
        )
        self.assertEqual(
            next(label for label in self.table.labels if label["Color"] == "BLUE"),
            {"Sequence": 1, "Color": "BLUE", "Card": "C7"},
        )

    def test_changing_label_color_closes_old_gap_and_reorders_new_color(self):
        self.table.labels = [
            {"Sequence": 1, "Color": "RED", "Card": "S7"},
            {"Sequence": 2, "Color": "RED", "Card": "H7"},
            {"Sequence": 1, "Color": "BLUE", "Card": "D7"},
            {"Sequence": 1, "Color": "GREEN", "Card": "C7"},
        ]

        self.table._set_card_label("S7", "BLUE", 1)

        sequences = {
            (label["Color"], label["Card"]): label["Sequence"]
            for label in self.table.labels
        }
        self.assertEqual(sequences[("RED", "H7")], 1)
        self.assertEqual(sequences[("BLUE", "S7")], 1)
        self.assertEqual(sequences[("BLUE", "D7")], 2)
        self.assertEqual(sequences[("GREEN", "C7")], 1)

    def test_reset_restores_initial_analysis_state(self):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="1NT PASS PASS PASS",
            declarer="SOUTH",
            contract="1NT",
        )
        self.table.load_board(self.board, self.configuration, scenario)
        initial_hands = {
            seat: {
                suit: list(ranks)
                for suit, ranks in hand.items()
            }
            for seat, hand in self.table.game.hands.items()
        }
        for _ in range(2):
            player = self.table.game.current_player
            card = self.table.game.get_legal_cards(player)[0]
            self.table.on_card_selected(player, card)

        self.assertTrue(self.table.move_history)
        for _ in range(2):
            player = self.table.game.current_player
            card = self.table.game.get_legal_cards(player)[0]
            self.table.on_card_selected(player, card)
        self.assertTrue(self.table.game.completed_tricks)
        self.assertTrue(self.table.played_card_widgets)
        self.table.btn_reset.click()

        self.assertEqual(self.table.move_history, [])
        self.assertEqual(self.table.game.current_player, "WEST")
        self.assertEqual(self.table.game.current_trick, [])
        self.assertEqual(self.table.game.completed_tricks, [])
        self.assertEqual(self.table.played_card_widgets, {})
        self.assertEqual(self.table.game.hands, initial_hands)
        self.assertTrue(
            all(len(hand.cards) == 13 for hand in self.table.hand_widgets.values())
        )
        self.assertFalse(self.table.btn_reset.isEnabled())

    def test_label_sequence_defaults_to_count_plus_one_for_selected_color(self):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="1NT PASS PASS PASS",
            declarer="SOUTH",
            contract="1NT",
        )
        self.table.load_board(self.board, self.configuration, scenario)
        self.table.labels = [
            {"Sequence": 1, "Color": "RED", "Card": "S8"},
            {"Sequence": 2, "Color": "RED", "Card": "S9"},
            {"Sequence": 1, "Color": "BLUE", "Card": "H8"},
        ]

        with patch("src.ui.views.table_view.LabelColorDialog") as dialog_type:
            dialog_type.return_value.exec.return_value = 0
            self.table.on_card_context_requested("WEST", "S7")

        dialog_type.assert_called_once()
        self.assertEqual(
            dialog_type.call_args.kwargs["sequence_counts"]["RED"],
            3,
        )
        self.assertEqual(
            dialog_type.call_args.kwargs["sequence_counts"]["BLUE"],
            2,
        )

    def test_right_clicking_card_opens_label_dialog_without_playing(self):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="1NT PASS PASS PASS",
            declarer="SOUTH",
            contract="1NT",
        )
        self.table.load_board(self.board, self.configuration, scenario)
        self.table.show()
        QApplication.processEvents()
        card = next(
            widget
            for widget in self.table.hand_widgets["WEST"].cards
            if widget.card_code == "S7"
        )

        with patch("src.ui.views.table_view.LabelColorDialog") as dialog_type:
            dialog_type.return_value.exec.return_value = 1
            dialog_type.return_value.selected_color = "BLUE"
            dialog_type.return_value.selected_sequence = 1
            QTest.mouseClick(card, Qt.MouseButton.RightButton)
            QTest.mouseClick(
                card,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.ControlModifier,
            )

        self.assertEqual(dialog_type.call_count, 2)
        self.assertEqual(
            dialog_type.call_args_list[0].args,
            ("S7", "RED", self.table),
        )
        self.assertEqual(
            dialog_type.call_args_list[1].args,
            ("S7", "BLUE", self.table),
        )
        self.assertEqual(self.table.game.current_player, "WEST")
        self.assertEqual(self.table.game.current_trick, [])
        self.assertEqual(self.table.labels[0]["Card"], "S7")
        self.assertEqual(self.table.labels[0]["Color"], "BLUE")
        self.assertEqual(self.table.labels[0]["Sequence"], 1)

    def test_real_label_dialog_installs_language_controller_without_crashing(self):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="1NT PASS PASS PASS",
            declarer="SOUTH",
            contract="1NT",
        )
        self.table.load_board(self.board, self.configuration, scenario)
        self.table.show()
        QApplication.processEvents()
        card = next(
            widget
            for widget in self.table.hand_widgets["WEST"].cards
            if widget.card_code == "S7"
        )

        with patch.object(QDialog, "exec", return_value=0):
            QTest.mouseClick(
                card,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.ControlModifier,
            )
            QTest.mouseClick(card, Qt.MouseButton.RightButton)

        self.table.language_controller.set_language("zh")
        self.table.language_controller.set_language("en")
        self.assertEqual(self.table.game.current_player, "WEST")
        self.assertEqual(self.table.game.current_trick, [])

    def test_card_dds_values_include_prior_tricks_for_the_side(self):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="1NT PASS PASS PASS",
            declarer="SOUTH",
            contract="1NT",
        )
        self.table.dds_wrapper.is_available = lambda: False
        self.table.load_board(self.board, self.configuration, scenario)
        self.table.game.tricks_won["WEST"] = 2
        self.table.game.completed_tricks = [[], []]
        self.table.dds_wrapper.is_available = lambda: True
        self.table.dds_wrapper.solve_board_pbn = lambda *args, **kwargs: {
            "cards": 1,
            "score": [5],
        }

        total_west_tricks = self.table._solve_dds_after_card("WEST", "S7")

        self.assertEqual(total_west_tricks, 8)
        self.table.dds_display_mode = "CONTRACT_OFFSET"
        self.assertEqual(
            self.table._format_card_dds_value("WEST", total_west_tricks),
            -2,
        )

    def test_robot_card_play_uses_a_slide_animation(self):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="1NT PASS PASS PASS",
            declarer="SOUTH",
            contract="1NT",
        )
        self.table.load_board(self.board, self.configuration, scenario)
        self.table.robot = FirstLegalRobot(self.table)
        self.assertTrue(self.table.set_mode("DEMONSTRATION"))

        for _ in range(
            (self.table.ROBOT_MOVE_DELAY_MS + 1000) // 20
        ):
            if self.table.robot_animation is not None:
                break
            QTest.qWait(20)

        self.assertEqual(self.table.game.current_player, "NORTH")
        self.assertIsNotNone(self.table.robot_animation)
        self.assertEqual(
            self.table.robot_animation.duration(),
            self.table.ROBOT_CARD_ANIMATION_MS,
        )

    def test_dds_matrix_has_room_for_all_rows_without_scrollbars(self):
        self.assertEqual(self.table.dds_result_table.height(), 180)
        self.assertEqual(
            self.table.dds_result_table.verticalScrollBarPolicy(),
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
        )
        self.assertIn(
            "QTableCornerButton::section",
            self.table.dds_result_table.styleSheet(),
        )

    def test_dds_matrix_can_be_hidden_to_free_table_space(self):
        self.assertFalse(self.table.dds_result_table.isHidden())
        self.assertEqual(self.table.btn_toggle_dds_matrix.text(), "Hide DDS")

        self.table.btn_toggle_dds_matrix.click()

        self.assertTrue(self.table.dds_result_table.isHidden())
        self.assertEqual(self.table.btn_toggle_dds_matrix.text(), "Show DDS")

        self.table.btn_toggle_dds_matrix.click()

        self.assertFalse(self.table.dds_result_table.isHidden())
        self.assertEqual(self.table.btn_toggle_dds_matrix.text(), "Hide DDS")
        self.assertEqual(
            self.table.dds_result_table.horizontalScrollBarPolicy(),
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
        )

    def test_dds_result_displays_the_native_res_table(self):
        table = [[7, 5, 7, 5], [5, 7, 5, 7], [7, 5, 7, 5], [5, 7, 5, 7], [5, 5, 5, 5]]
        self.table.dds_wrapper.is_available = lambda: True
        self.table.dds_wrapper.calc_dd_table_pbn = lambda _: {"res_table": table}

        self.table._refresh_dds_result(
            {
                "NORTH": "AKQJ.T98.765.432",
                "EAST": "432.AKQJ.T98.765",
                "SOUTH": "T98.765.AKQJ.T98",
                "WEST": "765.432.432.AKQJ",
            }
        )

        self.assertEqual(self.table.dds_result_table.rowCount(), 4)
        self.assertEqual(self.table.dds_result_table.columnCount(), 5)
        self.assertEqual(
            [
                self.table.dds_result_table.horizontalHeaderItem(column).text()
                for column in range(5)
            ],
            ["S", "H", "D", "C", "NT"],
        )
        self.assertEqual(
            [
                self.table.dds_result_table.verticalHeaderItem(row).text()
                for row in range(4)
            ],
            ["N", "S", "W", "E"],
        )
        self.assertEqual(self.table.dds_result_table.item(0, 0).text(), "7")
        self.assertEqual(self.table.dds_result_table.item(1, 4).text(), "5")

    def test_dds_matrix_switches_to_contract_offset(self):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="1NT PASS PASS PASS",
            declarer="SOUTH",
            contract="1NT",
        )
        self.table.load_board(self.board, self.configuration, scenario)
        self.table.dds_trick_table = [
            [8, 5, 6, 4],
            [5, 7, 4, 6],
            [6, 4, 7, 5],
            [4, 6, 5, 7],
            [5, 5, 5, 5],
        ]

        self.table.btn_dds_display.click()

        self.assertEqual(self.table.btn_dds_display.text(), "DDS: Contract ±")
        self.assertEqual(self.table.dds_result_table.item(0, 0).text(), "2")
        self.assertEqual(self.table.dds_result_table.item(1, 4).text(), "0")

    def test_dds_contract_matrix_counts_tricks_above_six(self):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="4S PASS PASS PASS",
            declarer="SOUTH",
            contract="4S",
        )
        self.table.load_board(self.board, self.configuration, scenario)
        self.table.dds_trick_table = [
            [8, 5, 6, 4],
            [5, 7, 4, 6],
            [6, 4, 7, 5],
            [4, 6, 5, 7],
            [5, 5, 5, 5],
        ]

        self.table.btn_dds_display.click()

        self.assertEqual(self.table.dds_result_table.item(0, 0).text(), "2")
        self.assertEqual(self.table.dds_result_table.item(0, 3).text(), "0")

    def test_demonstration_result_formats_contract_and_doubling(self):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="4H PASS PASS PASS",
            declarer="SOUTH",
            contract="4H",
            risk_status="REDOUBLE",
        )
        self.table.load_board(self.board, self.configuration, scenario)
        self.table.game.tricks_won.update(
            {"NORTH": 5, "SOUTH": 5, "EAST": 2, "WEST": 1}
        )
        self.assertEqual(self.table._demonstration_result(), "4HXX=")

        self.table.scenario.contract = "1NT"
        self.table.game.risk_status = "NONE"
        self.table.game.tricks_won.update(
            {"NORTH": 4, "SOUTH": 4, "EAST": 2, "WEST": 3}
        )
        self.assertEqual(self.table._demonstration_result(), "1NT+1")

        self.table.scenario.contract = "6S"
        self.table.game.risk_status = "DOUBLE"
        self.table.game.tricks_won.update(
            {"NORTH": 5, "SOUTH": 6, "EAST": 1, "WEST": 1}
        )
        self.assertEqual(self.table._demonstration_result(), "6SX-1")

    def test_completed_demonstration_shows_result_once(self):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="4H PASS PASS PASS",
            declarer="SOUTH",
            contract="4H",
            risk_status="REDOUBLE",
        )
        self.table.load_board(self.board, self.configuration, scenario)
        self.table.game.tricks_won.update(
            {"NORTH": 5, "SOUTH": 5, "EAST": 2, "WEST": 1}
        )
        self.table.current_mode = "DEMONSTRATION"

        with (
            patch.object(self.table, "_is_board_complete", return_value=True),
            patch("src.ui.views.table_view.show_message") as show_message,
        ):
            self.table._update_center_info()
            self.table._update_center_info()

        show_message.assert_called_once_with(
            self.table,
            "information",
            "Demonstration complete",
            "Final result: 4HXX=",
        )

    def test_center_message_is_separate_from_centered_played_cards(self):
        self.table.load_board(self.board, self.configuration)
        QApplication.processEvents()

        self.table._play_card("WEST", "S7")
        self.table._render_played_cards()
        self.table.center_info.setText("Several lines of changing status text.")
        self.table._render_played_cards()

        self.assertEqual(
            self.table.center_info.parentWidget(),
            self.table,
        )
        self.assertIs(
            self.table.played_card_area.parentWidget(),
            self.table.trick_area,
        )

    def test_analysis_cards_show_dds_tricks_and_contract_margin(self):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="1NT PASS PASS PASS",
            declarer="SOUTH",
            contract="1NT",
        )
        self.table.load_board(self.board, self.configuration, scenario)
        self.table.dds_wrapper.is_available = lambda: True
        legal_cards = self.table.game.get_legal_cards("WEST")
        solver_calls = []

        def solve_board(*args, **kwargs):
            solver_calls.append(kwargs)
            candidate_rank = kwargs["current_trick_rank"][0]
            return {
                "cards": 1,
                "score": [7 if candidate_rank == 7 else 6],
            }

        self.table.dds_wrapper.solve_board_pbn = solve_board

        self.table._refresh_card_dds_results()
        self.assertEqual(len(solver_calls), len(legal_cards))
        self.assertEqual(solver_calls[-1]["solutions"], 3)
        west_cards = {
            card.card_code: card for card in self.table.hand_widgets["WEST"].cards
        }
        self.assertEqual(west_cards["S7"].dds_tricks, 6)
        self.assertEqual(west_cards["S7"].dds_label.text(), "6")

        self.table.btn_dds_display.click()

        self.assertEqual(west_cards["S7"].dds_tricks, 0)
        self.assertEqual(west_cards["S7"].dds_label.text(), "0")

    def test_unavailable_dds_leaves_the_matrix_empty(self):
        self.table.dds_wrapper.is_available = lambda: False
        self.table._refresh_dds_result({})

        self.assertTrue(
            all(
                self.table.dds_result_table.item(row, column).text() == ""
                for row in range(4)
                for column in range(5)
            )
        )

    def test_played_trick_stays_visible_until_the_next_trick_and_undo_restores_it(self):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="1NT PASS PASS PASS",
            declarer="SOUTH",
            contract="1NT",
            is_targeted=1,
            targeted_sequence='["S7"]',
        )
        self.table.load_board(self.board, self.configuration, scenario)

        plays = [
            ("WEST", "S7"),
            ("NORTH", "SA"),
            ("EAST", "S2"),
            ("SOUTH", "ST"),
        ]
        for player, card in plays:
            self.assertTrue(self.table._play_card(player, card))
            self.table._render_hands()

        self.assertEqual(set(self.table.played_card_widgets), {
            "WEST", "NORTH", "EAST", "SOUTH",
        })
        self.assertTrue(
            all(card.width() > 36 and card.height() > 50
                for card in self.table.played_card_widgets.values())
        )
        self.assertEqual(len(self.table.game.completed_tricks), 1)
        self.assertEqual(self.table.game.current_trick, [])

        self.assertTrue(self.table._play_card("NORTH", "SK"))
        self.table._render_hands()
        self.assertEqual(set(self.table.played_card_widgets), {"NORTH"})

        self.table.play_previous_move()
        self.assertEqual(
            set(self.table.played_card_widgets),
            {"WEST", "NORTH", "EAST", "SOUTH"},
        )
        self.assertEqual(len(self.table.game.completed_tricks), 1)
        self.assertEqual(self.table.game.current_trick, [])

    def test_invalid_scenario_does_not_replace_the_loaded_board(self):
        self.table.load_board(self.board, self.configuration)
        loaded_game = self.table.game
        invalid_scenario = Scenario(
            id=2,
            board_id=1,
            bidding_route="8NT",
            declarer="SOUTH",
        )

        with self.assertRaises(ValueError):
            self.table.load_board(
                self.board,
                self.configuration,
                invalid_scenario,
            )

        self.assertIs(self.table.game, loaded_game)
        self.assertIsNone(self.table.scenario)


if __name__ == "__main__":
    unittest.main()
