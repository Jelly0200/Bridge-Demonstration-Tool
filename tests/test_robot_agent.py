import unittest
from unittest.mock import Mock

from src.core.bridge_game import BridgeGameEngine
from src.robot.robot_agent import RobotAgent


class TestRobotAgent(unittest.TestCase):
    def setUp(self):
        hands = {
            "NORTH": "AKQJ.T98.765.432",
            "EAST": "432.AKQJ.T98.765",
            "SOUTH": "T98.765.AKQJ.T98",
            "WEST": "765.432.432.AKQJ",
        }
        self.game = BridgeGameEngine(hands, dealer="SOUTH")
        self.game.start_play("2H", "SOUTH")
        self.assertTrue(self.game.play_card("WEST", "H2"))

    def test_unlabeled_robot_plays_a_dds_optimal_card_from_current_position(self):
        dds = Mock()
        dds.is_available.return_value = True
        dds.solve_board_pbn.return_value = {
            "cards": 3,
            "suit": (1, 1, 1),
            "rank": (9, 10, 8),
            "score": (7, 8, 8),
        }
        robot = RobotAgent(self.game, dds)

        card = robot.select_move(
            "NORTH",
            [],
            self.game.get_current_pbn_deal(),
        )

        self.assertEqual(card, "HT")
        dds.solve_board_pbn.assert_called_once_with(
            self.game.get_current_pbn_deal(),
            trump=1,
            first=3,
            current_trick_suit=(1, 0, 0),
            current_trick_rank=(2, 0, 0),
            target=-1,
            solutions=3,
            mode=0,
        )

    def test_unlabeled_robot_uses_legal_fallback_when_dds_is_unavailable(self):
        dds = Mock()
        dds.is_available.return_value = False
        robot = RobotAgent(self.game, dds)

        self.assertEqual(
            robot.select_move("NORTH", [], self.game.get_current_pbn_deal()),
            self.game.get_legal_cards("NORTH")[0],
        )

    def test_robot_applies_green_label_while_following_suit(self):
        dds = Mock()
        dds.is_available.return_value = True
        dds.solve_board_pbn.return_value = {
            "cards": 3,
            "suit": (1, 1, 1),
            "rank": (9, 10, 8),
            "score": (7, 8, 8),
        }
        robot = RobotAgent(self.game, dds)

        card = robot.select_move(
            "NORTH",
            [{"Sequence": 1, "Color": "GREEN", "Card": "H8"}],
            self.game.get_current_pbn_deal(),
        )

        self.assertEqual(card, "H8")

    def test_robot_ignores_nonbest_green_when_dds_available(self):
        dds = Mock()
        dds.is_available.return_value = True
        dds.solve_board_pbn.return_value = {
            "cards": 3,
            "suit": (1, 1, 1),
            "rank": (9, 10, 8),
            "score": (8, 9, 8),
        }
        robot = RobotAgent(self.game, dds)

        card = robot.select_move(
            "NORTH",
            [{"Sequence": 1, "Color": "GREEN", "Card": "H8"}],
            self.game.get_current_pbn_deal(),
        )

        self.assertEqual(card, "HT")

    def test_robot_does_not_use_yellow_when_dds_is_unavailable(self):
        dds = Mock()
        dds.is_available.return_value = False
        robot = RobotAgent(self.game, dds)

        card = robot.select_move(
            "NORTH",
            [{"Sequence": 1, "Color": "YELLOW", "Card": "H8"}],
            self.game.get_current_pbn_deal(),
        )

        self.assertIsNone(card)

    def test_robot_applies_blue_label_when_void_and_discarding(self):
        self.game.hands["NORTH"]["H"] = []
        dds = Mock()
        dds.is_available.return_value = False
        robot = RobotAgent(self.game, dds)

        card = robot.select_move(
            "NORTH",
            [{"Sequence": 1, "Color": "BLUE", "Card": "SA"}],
            self.game.get_current_pbn_deal(),
        )

        self.assertEqual(card, "SA")

    def test_robot_applies_red_label_when_leading(self):
        self.game.current_trick.clear()
        self.game.current_player = "NORTH"
        dds = Mock()
        dds.is_available.return_value = False
        robot = RobotAgent(self.game, dds)

        card = robot.select_move(
            "NORTH",
            [{"Sequence": 1, "Color": "RED", "Card": "SQ"}],
            self.game.get_current_pbn_deal(),
        )

        self.assertEqual(card, "SQ")

    def test_blue_sequence_selects_first_labeled_discard(self):
        self.game.hands["NORTH"]["H"] = []
        dds = Mock()
        dds.is_available.return_value = True
        dds.solve_board_pbn.return_value = {
            "cards": 1,
            "suit": (0,),
            "rank": (14,),
            "equals": ((1 << 13) | (1 << 12) | (1 << 11),),
            "score": (8,),
        }
        robot = RobotAgent(self.game, dds)

        card = robot.select_move(
            "NORTH",
            [
                {"Sequence": 2, "Color": "BLUE", "Card": "SQ"},
                {"Sequence": 1, "Color": "BLUE", "Card": "SK"},
            ],
            self.game.get_current_pbn_deal(),
        )

        self.assertEqual(card, "SK")

    def test_following_blue_label_only_selects_dds_best_candidates(self):
        dds = Mock()
        dds.is_available.return_value = True
        dds.solve_board_pbn.return_value = {
            "cards": 3,
            "suit": (1, 1, 1),
            "rank": (9, 10, 8),
            "score": (7, 8, 8),
        }
        robot = RobotAgent(self.game, dds)

        card = robot.select_move(
            "NORTH",
            [
                {"Sequence": 1, "Color": "BLUE", "Card": "H9"},
                {"Sequence": 2, "Color": "BLUE", "Card": "HT"},
            ],
            self.game.get_current_pbn_deal(),
        )

        self.assertEqual(card, "HT")

    def test_blue_label_can_select_equivalent_rank_while_discarding(self):
        self.game.hands["NORTH"]["H"] = []
        dds = Mock()
        dds.is_available.return_value = True
        dds.solve_board_pbn.return_value = {
            "cards": 1,
            "suit": (0,),
            "rank": (14,),
            "equals": ((1 << 13) | (1 << 12) | (1 << 11),),
            "score": (8,),
        }
        robot = RobotAgent(self.game, dds)

        card = robot.select_move(
            "NORTH",
            [
                {"Sequence": 1, "Color": "BLUE", "Card": "SK"},
                {"Sequence": 2, "Color": "BLUE", "Card": "SQ"},
            ],
            self.game.get_current_pbn_deal(),
        )

        self.assertEqual(card, "SK")


if __name__ == "__main__":
    unittest.main()
