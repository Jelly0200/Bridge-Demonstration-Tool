import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QStackedWidget,
    QTextBrowser,
)

from src.database.models.case_board import Board, BoardConfiguration
from src.database.models.scenario import Label, Scenario
from src.ui.views.table_view import TableView
from src.ui.widgets.bidding_box import BiddingBoxDialog
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
        self.assertIn("1NT", self.table.center_info.text())
        self.assertNotIn("NONE", self.table.center_info.text())
        self.assertNotIn("Test board", self.table.center_info.text())
        self.assertEqual(
            [
                item.widget().text()
                for item in (
                    self.table.top_bar_layout.itemAt(index)
                    for index in range(self.table.top_bar_layout.count())
                )
                if item.widget() is not None
                and hasattr(item.widget(), "text")
            ],
            ["Bidding", "Start"],
        )

    def test_contract_doubling_status_is_derived_from_bidding_route(self):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="1H DBL PASS PASS PASS",
            declarer="SOUTH",
            contract="1H",
            risk_status="NONE",
        )

        self.table.load_board(self.board, self.configuration, scenario)

        self.assertEqual(scenario.risk_status, "DOUBLE")
        self.assertEqual(self.table.game.risk_status, "DOUBLE")

    def test_all_hands_use_the_same_card_size(self):
        self.table.load_board(self.board, self.configuration)

        west_hand = self.table.hand_widgets["WEST"]
        self.assertFalse(west_hand.horizontal)
        self.assertEqual(west_hand.main_layout.count(), 4)
        self.assertTrue(all(not card.compact for card in west_hand.cards))
        self.assertTrue(
            all((card.width(), card.height()) == (50, 70) for card in west_hand.cards)
        )

        north_hand = self.table.hand_widgets["NORTH"]
        self.assertTrue(north_hand.horizontal)
        self.assertEqual(north_hand.main_layout.count(), 1)
        self.assertTrue(
            all((card.width(), card.height()) == (50, 70) for card in north_hand.cards)
        )

    def test_card_size_preference_resizes_all_hands(self):
        self.table.load_board(self.board, self.configuration)

        self.assertEqual(self.table.card_size_slider.minimum(), 35)
        self.assertEqual(self.table.card_size_slider.maximum(), 50)
        self.table.card_size_slider.setValue(35)
        self.assertEqual(self.table.card_size, 35)
        self.assertTrue(
            all(
                (card.width(), card.height()) == (35, 51)
                for hand in self.table.hand_widgets.values()
                for card in hand.cards
            )
        )

        self.table.card_size_slider.setValue(50)
        self.assertEqual(self.table.card_size, 50)
        self.assertTrue(
            all(
                (card.width(), card.height()) == (50, 70)
                for hand in self.table.hand_widgets.values()
                for card in hand.cards
            )
        )

    def test_application_font_preferences_update_and_validate(self):
        self.assertEqual(self.table.font_size_slider.minimum(), 10)
        self.assertEqual(self.table.font_size_slider.maximum(), 24)
        self.table.font_size_slider.setValue(20)
        self.table.set_application_font_color("#123456")

        self.assertEqual(self.table.application_font_size, 20)
        self.assertEqual(self.table.application_font_color, "#123456")
        self.assertEqual(self.table.get_admin_preferences()["font_size_px"], 20)
        self.assertEqual(self.table.get_admin_preferences()["font_color"], "#123456")
        with self.assertRaises(ValueError):
            self.table.set_application_font_color("not-a-color")

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

    def test_robot_sound_choices_can_be_changed_and_disabled(self):
        with patch("src.ui.views.table_view.QSoundEffect.play") as play:
            self.table._play_robot_card_sound()
            play.assert_called_once()

            self.table.set_robot_card_sound_choice("OFF")
            self.table._play_robot_card_sound()
            self.table.set_robot_card_sound_choice("CLASSIC")
            self.table._play_robot_card_sound()

        self.assertEqual(play.call_count, 2)
        self.assertEqual(self.table.robot_card_sound_choice, "CLASSIC")
        self.assertTrue(self.table.robot_card_sound_enabled)
        self.assertTrue(
            self.table.robot_card_sound.source().toLocalFile().endswith(
                "robot_card.wav"
            )
        )

    def test_card_sound_toggle_and_volume_setting_are_available(self):
        self.table.set_sound_volume(50)
        self.assertAlmostEqual(self.table.robot_card_sound.volume(), 0.5)
        with patch("src.ui.views.table_view.QSoundEffect.play") as play:
            self.table._play_robot_card_sound()
            play.assert_called_once()

        self.table.robot_card_sound_action.trigger()
        self.assertFalse(self.table.robot_card_sound_enabled)
        self.assertFalse(self.table.robot_card_sound_action.isChecked())
        with patch("src.ui.views.table_view.QSoundEffect.play") as play:
            self.table._play_robot_card_sound()
            play.assert_not_called()
        self.table.robot_card_sound_action.trigger()
        self.assertTrue(self.table.robot_card_sound_enabled)

    def test_preferred_view_mode_survives_loading_another_board(self):
        self.table.load_board(self.board, self.configuration)
        self.table.set_view_mode("HIDDEN")
        self.table.load_board(self.board, self.configuration)

        self.assertEqual(self.table.view_mode, "HIDDEN")
        self.assertTrue(self.table.view_actions["HIDDEN"].isChecked())

    def test_move_navigation_works_in_hidden_view(self):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="1NT PASS PASS PASS",
            declarer="SOUTH",
            contract="1NT",
            is_targeted=1,
            targeted_sequence='["S7", "S6"]',
        )
        self.table.load_board(self.board, self.configuration, scenario)
        self.table.set_view_mode("HIDDEN")

        self.table.play_next_move()
        self.assertEqual(self.table.target_index, 1)
        self.assertTrue(self.table.btn_prev.isEnabled())
        self.assertTrue(self.table.btn_reset.isEnabled())
        self.assertTrue(self.table.btn_next.isEnabled())

        self.table.btn_prev.click()
        self.assertEqual(self.table.target_index, 0)
        self.assertTrue(self.table.btn_next.isEnabled())
        self.table.btn_next.click()
        self.assertEqual(self.table.target_index, 1)
        self.table.btn_reset.click()
        self.assertEqual(self.table.target_index, 0)
        self.assertEqual(self.table.move_history, [])

    def test_board_only_center_shows_a_prompt_instead_of_board_details(self):
        self.table.load_board(self.board, self.configuration)

        center_text = self.table.center_info.text()
        self.assertIn("Double-click a scenario", center_text)
        self.assertNotIn("Test board", center_text)
        self.assertNotIn("Dealer:", center_text)
        self.assertNotIn("Vulnerability:", center_text)

    def test_record_button_tracks_the_dds_matrix_at_the_panel_top_right(self):
        self.table.resize(900, 700)
        self.table.show()
        self.application.processEvents()
        self.table.btn_record.show()
        self.table._position_overlay_widgets()

        self.assertIs(self.table.btn_record.parentWidget(), self.table)
        self.assertEqual(
            self.table.btn_record.geometry().right(),
            self.table.width() - 1,
        )
        self.assertEqual(
            self.table.btn_record.geometry().top(),
            self.table.dds_result_table.mapTo(
                self.table,
                QPoint(0, self.table.dds_result_table.height()),
            ).y() + self.table.RECORD_BUTTON_DDS_GAP,
        )
        self.table.set_dds_matrix_visible(False)
        self.assertEqual(self.table.btn_record.geometry().top(), 0)

    def test_move_navigation_controls_are_grouped_and_visible(self):
        self.table.resize(900, 700)
        self.table.show()
        self.application.processEvents()

        self.assertIs(
            self.table.btn_prev.parentWidget(),
            self.table.navigation_controls,
        )
        self.assertIs(
            self.table.btn_reset.parentWidget(),
            self.table.navigation_controls,
        )
        self.assertIs(
            self.table.btn_next.parentWidget(),
            self.table.navigation_controls,
        )
        self.assertTrue(self.table.navigation_controls.isVisible())
        self.assertTrue(
            all(
                button.isVisible()
                for button in (
                    self.table.btn_prev,
                    self.table.btn_reset,
                    self.table.btn_next,
                )
            )
        )
        self.assertEqual(
            self.table.footer_controls.geometry().bottom(),
            self.table.height() - 1,
        )
        self.assertEqual(
            self.table.footer_controls.geometry().right(),
            self.table.width() - 1,
        )

    def test_footer_controls_stay_visible_when_scenario_exceeds_viewport(self):
        stack = QStackedWidget()
        stack.setFixedSize(900, 850)
        table = TableView(parent=stack)
        stack.addWidget(table)
        table.load_board(
            self.board,
            self.configuration,
            Scenario(
                id=1,
                board_id=1,
                bidding_route="1NT PASS PASS PASS",
                declarer="SOUTH",
                contract="1NT",
            ),
        )
        stack.show()
        self.application.processEvents()

        self.assertGreater(table.height(), stack.height())
        footer_bottom = table.footer_controls.mapTo(
            stack,
            table.footer_controls.rect().bottomLeft(),
        ).y()
        self.assertEqual(
            footer_bottom,
            stack.height() - 1,
        )
        self.assertTrue(table.navigation_controls.isVisible())
        self.assertTrue(table.btn_human_seat.isVisible())

    def test_human_seat_button_cycles_and_is_bottom_right(self):
        self.table.resize(900, 700)
        self.table.show()
        self.application.processEvents()

        self.assertEqual(self.table.btn_human_seat.text(), "Human seat: SOUTH")
        self.assertEqual(
            self.table.btn_human_seat.geometry().right(),
            self.table.footer_controls.width() - 1,
        )
        self.assertEqual(
            self.table.btn_human_seat.geometry().bottom(),
            self.table.footer_controls.height() - 1,
        )
        self.table.btn_human_seat.click()
        self.assertEqual(self.table.current_side, "WEST")
        self.assertEqual(self.table.btn_human_seat.text(), "Human seat: WEST")
        self.table.language_controller.set_language("zh")
        self.assertEqual(self.table.btn_human_seat.text(), "人类座位：西")
        self.table.btn_human_seat.click()
        self.assertEqual(self.table.btn_human_seat.text(), "人类座位：北")

    def test_bidding_button_is_aligned_to_the_panel_top_left(self):
        self.table.resize(900, 700)
        self.table.show()
        self.application.processEvents()

        self.assertEqual(self.table.btn_bidding.geometry().left(), 0)
        self.assertEqual(
            self.table.btn_bidding.geometry().top(),
            self.table.top_bar_layout.geometry().top(),
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
        self.table.show()
        self.table.set_lockdown_mode(True)

        self.assertFalse(self.table.btn_bidding.isHidden())
        self.assertFalse(self.table.btn_prev.isHidden())
        self.assertFalse(self.table.btn_next.isHidden())
        self.assertFalse(self.table.btn_demonstration.isVisible())
        self.assertFalse(self.table.btn_record.isVisible())
        self.assertTrue(self.table.btn_reset.isVisible())
        self.assertTrue(self.table.btn_human_seat.isVisible())
        self.assertFalse(self.table.btn_human_seat.isEnabled())
        self.assertFalse(self.table.dds_visibility_action.isEnabled())
        self.assertTrue(self.table.dds_result_table.isHidden())

        self.table.set_lockdown_mode(False)
        self.assertTrue(self.table.view_actions["ANALYSIS"].isEnabled())

    def test_dds_matrix_is_flush_with_the_top_right_view_edges(self):
        self.table.show()
        self.application.processEvents()

        matrix_rect = self.table.dds_slot.geometry()
        footer_item_rect = self.table.footer_layout.itemAt(0).geometry()
        self.assertEqual(matrix_rect.right() + 1, self.table.width())
        self.assertEqual(matrix_rect.top(), 0)
        self.assertEqual(
            footer_item_rect.bottom() + 1,
            self.table.footer_controls.height(),
        )

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
        self.assertEqual(self.table.current_mode, "NORMAL")
        emitted_modes = []
        self.table.mode_changed.connect(emitted_modes.append)

        self.assertTrue(self.table.start_demonstration())
        QTest.qWait(
            self.table.ROBOT_MOVE_DELAY_MS
            + self.table.ROBOT_CARD_ANIMATION_MS
            + 100
        )

        self.assertEqual(self.table.current_mode, "DEMONSTRATION")
        self.assertEqual(emitted_modes, ["DEMONSTRATION"])
        locked_side = self.table.current_side
        locked_perspective = self.table.perspective
        locked_dds_mode = self.table.dds_display_mode
        self.table.select_side()
        self.table.rotate_perspective()
        self.table.toggle_dds_display_mode()
        self.assertEqual(self.table.current_side, locked_side)
        self.assertEqual(self.table.perspective, locked_perspective)
        self.assertEqual(self.table.dds_display_mode, locked_dds_mode)
        self.table.set_view_mode("HIDDEN")
        self.assertEqual(self.table.view_mode, "HIDDEN")
        self.table.set_view_mode("ANALYSIS")
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
        self.assertFalse(self.table.btn_human_seat.isEnabled())
        self.assertTrue(self.table.btn_bidding.isEnabled())
        self.assertTrue(self.table.bidding_action.isEnabled())
        self.assertFalse(self.table.description_action.isEnabled())
        self.assertTrue(self.table.label_action.isEnabled())
        self.assertFalse(self.table.btn_prev.isEnabled())
        self.assertFalse(self.table.btn_reset.isEnabled())
        self.assertFalse(self.table.btn_next.isEnabled())
        self.assertFalse(self.table.btn_record.isEnabled())
        self.assertFalse(self.table.btn_record.isHidden())

        self.table.set_mode("NORMAL")
        self.assertFalse(self.table.dds_result_table.isHidden())

    def test_start_end_toggle_controls_demonstration_once(self):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="1NT PASS PASS PASS",
            declarer="SOUTH",
            contract="1NT",
        )
        self.table.load_board(self.board, self.configuration, scenario)

        self.assertTrue(self.table.btn_demonstration.isEnabled())
        self.assertEqual(self.table.btn_demonstration.text(), "Start")
        self.table.mode_changed.connect(self.table.set_mode)
        with patch.object(self.table, "_advance_robots") as advance_robots:
            self.table.show()
            self.application.processEvents()
            click_point = self.table.btn_demonstration.mapTo(
                self.table,
                self.table.btn_demonstration.rect().center(),
            )
            self.assertIs(
                self.table.childAt(click_point),
                self.table.btn_demonstration,
            )
            QTest.mouseClick(
                self.table.btn_demonstration,
                Qt.MouseButton.LeftButton,
            )
            advance_robots.assert_called_once_with()
        self.assertEqual(self.table.current_mode, "DEMONSTRATION")
        self.assertTrue(self.table.btn_demonstration.isEnabled())
        self.assertEqual(self.table.btn_demonstration.text(), "End")

        QTest.mouseClick(
            self.table.btn_demonstration,
            Qt.MouseButton.LeftButton,
        )
        self.assertEqual(self.table.current_mode, "NORMAL")
        self.assertTrue(self.table.btn_demonstration.isEnabled())
        self.assertEqual(self.table.btn_demonstration.text(), "Start")

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
        QTest.qWait(
            self.table.ROBOT_MOVE_DELAY_MS
            + self.table.ROBOT_CARD_ANIMATION_MS
            + 100
        )
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
        self.table.rule_actions["LABEL"].setChecked(True)
        self.table.current_side = human_seat
        self.table.robot = FirstLegalRobot(self.table)
        self.assertTrue(self.table.set_mode("DEMONSTRATION"))
        QTest.qWait(
            self.table.ROBOT_MOVE_DELAY_MS
            + self.table.ROBOT_CARD_ANIMATION_MS
            + 100
        )

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
        QTest.qWait(
            self.table.ROBOT_MOVE_DELAY_MS
            + self.table.ROBOT_CARD_ANIMATION_MS
            + 100
        )
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
        self.assertTrue(self.table.btn_next.isEnabled())

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
        self.assertEqual(east_cards["HA"].label_color, "NONE")
        self.assertIsNone(east_cards["HA"].label_sequence)

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
        self.assertEqual(self.table.view_mode, "HIDDEN")
        self.assertTrue(self.table.set_mode("DEMONSTRATION"))

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

    def test_record_button_saves_only_a_completed_analysis_play(self):
        self.table.load_board(self.board, self.configuration)
        self.assertFalse(self.table.btn_record.isEnabled())
        self.assertFalse(self.table.btn_record.isHidden())
        self.assertIn("scenario", self.table.btn_record.toolTip().lower())

        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="1NT PASS PASS PASS",
            is_targeted=1,
            targeted_sequence="[]",
        )
        self.table.load_board(self.board, self.configuration, scenario)
        self.assertFalse(self.table.btn_record.isEnabled())
        self.assertFalse(self.table.btn_record.isHidden())
        self.assertIn("52 cards", self.table.btn_record.toolTip().lower())
        for move_number in range(52):
            player = self.table.game.current_player
            card = self.table.game.get_legal_cards(player)[0]
            self.table.on_card_selected(player, card)
            if move_number == 50:
                self.assertFalse(self.table.btn_record.isEnabled())
        self.assertTrue(self.table._is_board_complete())
        self.assertTrue(self.table.btn_record.isEnabled())
        self.assertFalse(self.table.btn_record.isHidden())
        self.table.btn_record.click()
        self.assertEqual(len(self.table.target_sequence), 52)
        self.assertEqual(len(set(self.table.target_sequence)), 52)
        self.assertEqual(
            scenario.targeted_sequence,
            json.dumps(self.table.target_sequence),
        )
        self.assertEqual(scenario.is_targeted, 1)
        self.assertEqual(self.table.rule_mode, "TARGET")
        self.assertTrue(self.table._is_board_complete())
        self.assertEqual(len(self.table.game.completed_tricks), 13)

    def test_suit_symbol_size_updates_existing_and_new_cards(self):
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
        )

        south_hand = self.table.hand_widgets["SOUTH"]
        dds_font_size = south_hand.cards[0].dds_label.font().pointSize()
        self.assertEqual(dds_font_size, 9)
        self.table.set_suit_symbol_size(35)

        self.assertTrue(south_hand.cards)
        self.assertTrue(
            all(card.card_label.font().pointSize() == 37 for card in south_hand.cards)
        )
        self.assertTrue(
            all(
                card.dds_label.font().pointSize() == dds_font_size
                for card in south_hand.cards
            )
        )
        self.table.set_card_size(44)
        self.assertTrue(
            all(card.card_label.font().pointSize() == 35 for card in south_hand.cards)
        )

        player = self.table.game.current_player
        card = self.table.game.get_legal_cards(player)[0]
        self.table.on_card_selected(player, card)
        played_card = self.table._played_card_widget_pool[player]
        self.assertEqual(played_card.card_label.font().pointSize(), 35)

    def test_admin_preferences_include_card_suit_symbol_size(self):
        self.table.set_suit_symbol_size(34)

        self.assertEqual(
            self.table.get_admin_preferences()["card_suit_symbol_size_px"],
            34,
        )
        self.table.apply_admin_preferences(
            {
                **self.table.get_admin_preferences(),
                "card_suit_symbol_size_px": 35,
            }
        )
        self.assertEqual(self.table.suit_symbol_size, 35)
        self.assertEqual(self.table.suit_symbol_size_slider.value(), 35)

    def test_central_controls_are_limited_to_bidding_and_information(self):
        self.assertEqual(self.table.btn_bidding.text(), "Bidding")
        self.assertEqual(
            [action.text() for action in self.table.bidding_menu.actions()
             if not action.isSeparator()],
            ["Bidding", "Information"],
        )
        self.assertEqual(
            self.table.top_bar_layout.itemAt(0).widget(),
            self.table.btn_bidding,
        )
        self.assertEqual(
            self.table.top_bar_layout.itemAt(1).widget(),
            self.table.btn_demonstration,
        )
        self.assertIs(self.table.dds_slot.parentWidget(), self.table)
        self.assertEqual(
            self.table.footer_layout.itemAt(0).widget(),
            self.table.navigation_controls,
        )
        self.assertEqual(
            self.table.footer_layout.itemAt(2).widget(),
            self.table.btn_human_seat,
        )
        self.assertTrue(
            self.table.footer_layout.itemAt(0).alignment()
            & Qt.AlignmentFlag.AlignBottom
        )
        self.assertEqual(self.table.table_grid.contentsMargins().top(), 0)
        self.assertEqual(self.table.btn_record.text(), "Record target")
        self.assertEqual(self.table.btn_prev.text(), "Last move")
        self.assertEqual(self.table.btn_reset.text(), "Reset")
        self.assertEqual(self.table.btn_next.text(), "Next move")

    def test_robot_speed_slider_changes_playback_delay(self):
        self.table.robot_speed_slider.setValue(300)
        self.assertEqual(self.table.robot_move_delay_ms, 300)
        self.table.robot_speed_slider.setValue(2600)
        self.assertEqual(self.table.robot_move_delay_ms, 2600)

    def test_description_menu_displays_saved_scenario_information(self):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="1NT PASS PASS PASS",
            declarer="SOUTH",
            contract="1NT",
            name="Opening lead",
            information="Lead the singleton heart.",
        )
        self.table.load_board(self.board, self.configuration, scenario)
        dialogs = []
        with patch(
            "src.ui.views.table_view.exec_and_delete",
            side_effect=lambda dialog: dialogs.append(dialog),
        ):
            self.table.description_action.trigger()

        self.assertEqual(len(dialogs), 1)
        self.addCleanup(dialogs[0].close)
        self.assertEqual(
            dialogs[0].findChild(QTextBrowser, "informationText").toPlainText(),
            "Lead the singleton heart.",
        )
        self.assertEqual(self.table.scenario.information, "Lead the singleton heart.")

    def test_information_bar_is_centered_above_the_card_area(self):
        self.table.resize(900, 700)
        self.table.show()
        self.application.processEvents()

        info_top_left = self.table.center_info.mapTo(
            self.table,
            self.table.center_info.rect().topLeft(),
        )
        self.assertAlmostEqual(
            info_top_left.x() + self.table.center_info.width() // 2,
            self.table.rect().center().x(),
            delta=1,
        )
        self.assertLess(
            info_top_left.y() + self.table.center_info.height(),
            self.table.table_canvas.geometry().top(),
        )
        self.assertIn("rgba(", self.table.center_info.styleSheet())

    def test_empty_suits_are_not_decorated_on_vertical_hands(self):
        west_hand = self.table.hand_widgets["WEST"]
        west_hand.set_hand(["SA"])

        suit_rows = [
            west_hand.main_layout.itemAt(index).layout()
            for index in range(west_hand.main_layout.count())
        ]
        self.assertEqual(
            [row.itemAt(0).widget() is not None for row in suit_rows],
            [True, False, False, False],
        )
        self.assertIsInstance(suit_rows[0].itemAt(0).widget(), CardWidget)
        self.assertEqual(
            [row.minimumSize().height() for row in suit_rows],
            [70, 70, 70, 70],
        )

    def test_vertical_suit_rows_stay_fixed_when_rotating(self):
        self.table.load_board(self.board, self.configuration)
        self.table.resize(1200, 1000)
        self.table.show()
        self.application.processEvents()

        for _ in range(4):
            vertical_hands = [
                hand
                for hand in self.table.hand_widgets.values()
                if not hand.horizontal
            ]
            self.assertEqual(len(vertical_hands), 2)
            for hand in vertical_hands:
                self.assertEqual(hand.main_layout.count(), 4)
                self.assertEqual(
                    [
                        hand.main_layout.itemAt(index)
                        .layout()
                        .minimumSize()
                        .height()
                        for index in range(4)
                    ],
                    [70, 70, 70, 70],
                )
                self.assertEqual(
                    [
                        hand.main_layout.itemAt(index).layout().geometry().height()
                        for index in range(4)
                    ],
                    [70, 70, 70, 70],
                )
            self.table.rotate_perspective()
            self.application.processEvents()

    def test_left_and_right_card_gap_stays_fixed_when_rotating(self):
        self.table.load_board(self.board, self.configuration)
        self.table.resize(1200, 1000)
        self.table.show()
        self.application.processEvents()
        gaps = []

        for _ in range(4):
            vertical_hands = [
                hand
                for hand in self.table.hand_widgets.values()
                if not hand.horizontal
            ]
            left_hand = min(
                vertical_hands,
                key=lambda hand: hand.mapTo(
                    self.table,
                    hand.rect().center(),
                ).x(),
            )
            right_hand = max(
                vertical_hands,
                key=lambda hand: hand.mapTo(
                    self.table,
                    hand.rect().center(),
                ).x(),
            )
            left_edge = max(
                card.mapTo(self.table, card.rect().topLeft()).x() + card.width()
                for card in left_hand.cards
            )
            right_edge = min(
                card.mapTo(self.table, card.rect().topLeft()).x()
                for card in right_hand.cards
            )
            gaps.append(right_edge - left_edge)
            self.table.rotate_perspective()
            self.application.processEvents()

        self.assertEqual(len(set(gaps)), 1)

    def test_card_area_is_centered_in_the_panel(self):
        self.table.resize(900, 700)
        self.table.show()
        self.application.processEvents()

        self.assertAlmostEqual(
            self.table.table_canvas.geometry().center().x(),
            self.table.rect().center().x(),
            delta=1,
        )
        trick_center = self.table.trick_area.mapTo(
            self.table,
            self.table.trick_area.rect().center(),
        )
        self.assertAlmostEqual(
            trick_center.x(),
            self.table.rect().center().x(),
            delta=1,
        )
        self.assertAlmostEqual(
            trick_center.y(),
            self.table.rect().center().y(),
            delta=1,
        )

    def test_dds_matrix_does_not_overlap_top_hand_at_minimum_size(self):
        self.table.load_board(self.board, self.configuration)
        self.table.resize(self.table.minimumWidth(), self.table.minimumHeight())
        self.table.show()
        self.application.processEvents()

        north_card_top = self.table.hand_widgets["NORTH"].cards[0].mapTo(
            self.table,
            self.table.hand_widgets["NORTH"].cards[0].rect().topLeft(),
        ).y()
        self.assertGreaterEqual(
            north_card_top,
            self.table.dds_slot.geometry().bottom() + 1,
        )

    def test_language_switch_translates_live_text_and_keeps_dds_labels(self):
        self.table.language_controller.set_language("zh")

        self.assertEqual(self.table.btn_bidding.text(), "叫牌")
        self.assertEqual(self.table.btn_demonstration.text(), "开始")
        self.assertEqual(self.table.dds_visibility_action.text(), "Show DDS matrix")

        self.table.center_info.setText("Play complete.")
        self.assertEqual(self.table.center_info.text(), "牌局已结束。")

        self.table.language_controller.set_language("en")
        self.assertEqual(self.table.btn_bidding.text(), "Bidding")
        self.assertEqual(self.table.btn_demonstration.text(), "Start")
        self.assertEqual(self.table.center_info.text(), "Play complete.")

    def test_label_definition_action_opens_definition_without_changing_rule_mode(self):
        self.table._update_scenario_controls()
        self.assertIsNone(self.table.scenario)
        self.assertTrue(self.table.label_action.isEnabled())
        self.table.rule_mode = "TARGET"
        dialog = QDialog(self.table)
        self.addCleanup(dialog.close)

        with (
            patch(
                "src.ui.views.table_view.LabelDefinitionDialog",
                return_value=dialog,
            ) as dialog_class,
            patch("src.ui.views.table_view.exec_and_delete") as execute_dialog,
        ):
            self.table.label_action.trigger()

        dialog_class.assert_called_once()
        execute_dialog.assert_called_once_with(dialog)
        self.assertEqual(self.table.rule_mode, "TARGET")

    def test_test_playback_uses_read_only_analysis_bidding_dialog(self):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="1NT PASS PASS PASS",
            declarer="SOUTH",
            contract="1NT",
            information="The auction establishes the contract.",
        )
        self.table.load_board(
            self.board,
            self.configuration,
            scenario,
            test_playback=True,
        )
        dialogs = []

        with patch(
            "src.ui.views.table_view.exec_and_delete",
            side_effect=dialogs.append,
        ):
            self.table.open_settings()

        dialog = dialogs[0]
        self.assertIsInstance(dialog, BiddingBoxDialog)
        self.assertTrue(dialog.read_only)
        self.assertTrue(dialog.route_only)
        self.assertEqual(
            dialog.bidding_history,
            ["1NT", "PASS", "PASS", "PASS"],
        )
        self.assertTrue(
            all(
                not button.isEnabled()
                for button in dialog.call_buttons.values()
            )
        )
        self.assertTrue(
            all(
                not button.isEnabled()
                for button in dialog.special_buttons.values()
            )
        )
        self.assertFalse(dialog.btn_undo.isEnabled())
        self.assertFalse(dialog.btn_save.isVisible())
        self.assertEqual(dialog.btn_cancel.text(), "Close")
        self.table.current_mode = "DEMONSTRATION"
        self.table.lockdown_mode = True
        self.table._update_scenario_controls()
        self.assertTrue(self.table.description_action.isEnabled())
        with (
            patch(
                "src.ui.views.table_view.TestScenarioDialog"
            ) as information_dialog,
            patch("src.ui.views.table_view.exec_and_delete"),
        ):
            self.table.show_description()
        self.assertEqual(
            information_dialog.call_args.kwargs["information"],
            "The auction establishes the contract.",
        )
        dialog.add_call("2NT")
        dialog.undo_call()
        self.assertEqual(
            dialog.bidding_history,
            ["1NT", "PASS", "PASS", "PASS"],
        )
        self.assertEqual(self.table.card_size, 43)
        self.assertTrue(self.table.navigation_controls.isHidden())
        self.assertTrue(self.table.btn_human_seat.isHidden())
        self.assertEqual(self.table.center_info.font().pixelSize(), 20)
        self.assertEqual(self.table.btn_bidding.font().pixelSize(), 18)

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
        self.assertEqual(card.rank_label.font().pointSize(), 16)
        self.assertEqual(card.card_label.font().pointSize(), 32)
        self.assertEqual(card.dds_label.font().pointSize(), 9)
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
        original_slot_geometry = self.table.dds_slot.geometry()

        self.table.dds_visibility_action.trigger()

        self.assertTrue(self.table.dds_result_table.isHidden())
        self.assertEqual(self.table.dds_slot.geometry(), original_slot_geometry)

        self.table.dds_visibility_action.trigger()

        self.assertFalse(self.table.dds_result_table.isHidden())
        self.assertEqual(self.table.dds_slot.geometry(), original_slot_geometry)
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

        self.table.set_dds_display_mode("CONTRACT_OFFSET")

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

        self.table.set_dds_display_mode("CONTRACT_OFFSET")

        self.assertEqual(self.table.dds_result_table.item(0, 0).text(), "2")
        self.assertEqual(self.table.dds_result_table.item(0, 3).text(), "0")

    def test_demonstration_result_formats_contract_and_doubling(self):
        scenario = Scenario(
            id=1,
            board_id=1,
            bidding_route="4H DBL PASS RDBL PASS PASS PASS",
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
            bidding_route="4H DBL PASS RDBL PASS PASS PASS",
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
            self.table.info_overlay,
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

        self.table.set_dds_display_mode("CONTRACT_OFFSET")

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
