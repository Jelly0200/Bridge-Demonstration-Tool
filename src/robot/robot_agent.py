# src/robot/robot_agent.py
from typing import List, Dict, Any, Optional
from src.core.bridge_game import BridgeGameEngine
from src.core.dds_wrapper import DdsWrapper
from src.robot.label_evaluator import LabelEvaluator
from config.constants import RANKS, SUITS


DDS_SEATS = ("NORTH", "EAST", "SOUTH", "WEST")
DDS_TRUMPS = {"S": 0, "H": 1, "D": 2, "C": 3, "NT": 4}


class RobotAgent:
    def __init__(self, game_engine: BridgeGameEngine, dds_wrapper: DdsWrapper):
        self.game = game_engine
        self.dds = dds_wrapper

    def select_move(self, player: str, labels: List[Dict[str, Any]], pbn_deal: str) -> Optional[str]:
        """
        Select the next card for the specified robot player.

        :param player: The player whose turn it is (SOUTH, WEST, NORTH, or EAST).
        :param labels: The scenario's card labels.
        :param pbn_deal: The current deal as a PBN string.
        """
        # 1. Get all cards currently legal for this player.
        legal_cards = self.game.get_legal_cards(player)
        if not legal_cards:
            return None

        # 2. Classify the play as leading, following suit, or discarding.
        if not self.game.current_trick:
            play_type = "leading"
        else:
            led_suit = self.game.current_trick[0][1][0]
            play_type = (
                "following"
                if any(card[0] == led_suit for card in legal_cards)
                else "discarding"
            )
        # 3. Get the DDS-recommended optimal cards when DDS is available.
        dds_card_scores = {}
        if self.dds.is_available():
            try:
                trick_suits = tuple(
                    SUITS.index(card[0]) for _, card in self.game.current_trick
                )
                trick_ranks = tuple(
                    RANKS.index(card[1:]) + 2
                    for _, card in self.game.current_trick
                )
                trick_leader = (
                    self.game.current_trick[0][0]
                    if self.game.current_trick
                    else player
                )
                solve_result = self.dds.solve_board_pbn(
                    pbn_deal,
                    trump=DDS_TRUMPS[self.game.trump_suit or "NT"],
                    first=DDS_SEATS.index(trick_leader),
                    current_trick_suit=trick_suits + (0,) * (3 - len(trick_suits)),
                    current_trick_rank=trick_ranks + (0,) * (3 - len(trick_ranks)),
                    target=-1,
                    solutions=3,
                    mode=0,
                )
                dds_card_scores = self._card_scores_from_result(solve_result)
            except Exception as e:
                print(f"[Robot] DDS solving failed; falling back to label evaluation: {e}")

        if not labels and not dds_card_scores:
            return legal_cards[0]

        # 4. Restrict label priorities to DDS-best cards, except Red/Blue overrides.
        selected_card = LabelEvaluator.evaluate_card_choice(
            legal_cards=legal_cards,
            dds_card_scores=dds_card_scores,
            labels=labels,
            play_type=play_type,
        )

        return selected_card

    @staticmethod
    def _card_scores_from_result(result: Any) -> Dict[str, int]:
        if not isinstance(result, dict):
            return {}

        card_count = result.get("cards")
        suits = result.get("suit")
        ranks = result.get("rank")
        scores = result.get("score")
        equals = result.get("equals")
        if (
            not isinstance(card_count, int)
            or card_count <= 0
            or not isinstance(suits, (list, tuple))
            or not isinstance(ranks, (list, tuple))
            or not isinstance(scores, (list, tuple))
        ):
            return {}

        count = min(card_count, len(suits), len(ranks), len(scores))
        if count <= 0:
            return {}
        card_scores = {}
        for index in range(count):
            suit = suits[index]
            rank = ranks[index]
            score = scores[index]
            if (
                not isinstance(suit, int)
                or not 0 <= suit < len(SUITS)
                or not isinstance(rank, int)
                or not 2 <= rank <= 14
                or not isinstance(score, int)
            ):
                continue

            card_scores[f"{SUITS[suit]}{RANKS[rank - 2]}"] = score
            if not isinstance(equals, (list, tuple)) or index >= len(equals):
                continue
            equivalent_ranks = equals[index]
            if not isinstance(equivalent_ranks, int) or equivalent_ranks < 0:
                continue
            for equivalent_rank in range(2, 15):
                if equivalent_ranks & (1 << equivalent_rank):
                    card_scores[
                        f"{SUITS[suit]}{RANKS[equivalent_rank - 2]}"
                    ] = score
        return card_scores

    @staticmethod
    def _optimal_cards_from_result(result: Any) -> List[str]:
        card_scores = RobotAgent._card_scores_from_result(result)
        if not card_scores:
            return []
        best_score = max(card_scores.values())
        return [
            card for card, score in card_scores.items()
            if score == best_score
        ]