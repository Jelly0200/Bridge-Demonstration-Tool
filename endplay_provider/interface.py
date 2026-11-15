import importlib
import importlib.util
from types import ModuleType
from typing import Any

from config.constants import RANKS, SUITS


class EndplayProvider:
    """Adapt Endplay's API to the application's DDS interface."""

    def __init__(self) -> None:
        self._dds: ModuleType = importlib.import_module("endplay.dds")
        self._solve: ModuleType = importlib.import_module("endplay.dds.solve")
        self._types: ModuleType = importlib.import_module("endplay.types")

    @staticmethod
    def is_installed() -> bool:
        try:
            return importlib.util.find_spec("endplay") is not None
        except (ImportError, ValueError):
            return False

    def calc_dd_table_pbn(self, pbn_deal: str) -> dict[str, Any]:
        deal = self._types.Deal(pbn_deal)
        table = self._dds.calc_dd_table(deal)
        denoms = (
            self._types.Denom.spades,
            self._types.Denom.hearts,
            self._types.Denom.diamonds,
            self._types.Denom.clubs,
            self._types.Denom.nt,
        )
        players = (
            self._types.Player.north,
            self._types.Player.east,
            self._types.Player.south,
            self._types.Player.west,
        )
        return {
            "res_table": [
                [table[denom, player] for player in players]
                for denom in denoms
            ]
        }

    def solve_board_pbn(
        self,
        pbn_deal: str,
        target: int = -1,
        solutions: int = 2,
        mode: int = 0,
        *,
        trump: int = 4,
        first: int = 0,
        current_trick_suit=(0, 0, 0),
        current_trick_rank=(0, 0, 0),
    ) -> dict[str, Any]:
        deal = self._types.Deal(
            pbn_deal,
            first=self._types.Player(first),
            trump=self._types.Denom(trump),
        )
        for suit, rank in zip(current_trick_suit, current_trick_rank):
            if rank == 0:
                continue
            card = f"{SUITS[suit]}{RANKS[rank - 2]}"
            deal.play(card, from_hand=False)

        solved = self._dds.solve_board(
            deal,
            mode=self._solve_mode(mode, solutions),
            target=target,
        )
        cards = list(solved)
        return {
            "cards": len(cards),
            "suit": [int(card.suit) for card, _score in cards],
            "rank": [
                RANKS.index(card.rank.abbr) + 2
                for card, _score in cards
            ],
            "score": [int(score) for _card, score in cards],
        }

    def _solve_mode(self, mode: int, solutions: int):
        solve_mode = self._solve.SolveMode
        if mode != 0:
            return solve_mode(mode)
        if solutions == 1:
            return solve_mode.OptimalOne
        if solutions == 2:
            return solve_mode.OptimalAll
        return solve_mode.Default
