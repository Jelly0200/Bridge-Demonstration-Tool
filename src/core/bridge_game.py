# src/core/bridge_game.py
from typing import List, Dict, Tuple, Optional
from src.core.pbn_parser import PbnParser
from src.core.bridge_logic import BridgeLogic
from config.constants import PLAYERS, PLAYER_NEXT, RANKS


class BridgeGameEngine:
    def __init__(self, hands: Dict[str, str], dealer: str = "NORTH", vulnerability: str = "NONE"):
        """
        Initialize the bridge game engine.
        :param hands: A mapping of player directions to PBN hand strings.
        :param dealer: The dealer ('NORTH', 'EAST', 'SOUTH', or 'WEST').
        :param vulnerability: The vulnerability ('NONE', 'NS', 'EW', or 'BOTH').
        """
        self.raw_hands = hands
        self.hands = {player: PbnParser.parse_hand(pbn) for player, pbn in hands.items()}
        self.dealer = dealer.upper()
        self.vulnerability = vulnerability.upper()

        # Track the auction state.
        self.bidding_history: List[str] = []
        self.current_bidder: str = self.dealer
        self.is_bidding_over: bool = False

        # Contract details are determined when the auction ends.
        self.contract: Optional[str] = None  # For example, "4S" or "3NT".
        self.trump_suit: Optional[str] = None  # 'S', 'H', 'D', 'C', or 'NT'.
        self.declarer: Optional[str] = None  # The declarer ('SOUTH', 'NORTH', 'EAST', or 'WEST').
        self.risk_status: str = "NONE"  # 'NONE', 'DOUBLE', 'REDOUBLE'

        # Track the play state.
        self.current_player: Optional[str] = None  # The next player to act; opening lead is left of declarer.
        self.current_trick: List[Tuple[str, str]] = []  # Current trick as (player, card) pairs.
        self.lead_suit: Optional[str] = None  # The suit led to the current trick.
        self.completed_tricks: List[List[Tuple[str, str]]] = []  # History of completed tricks.
        self.tricks_won: Dict[str, int] = {p: 0 for p in PLAYERS}  # Total tricks won by each player.

    # ==================== Bidding phase ====================

    def get_legal_bids(self) -> List[str]:
        """Return all legal calls for the current bidder."""
        if self.is_bidding_over:
            return []
        return BridgeLogic.get_legal_bids(self.bidding_history)

    def make_bid(self, player: str, bid: str) -> bool:
        """
        Make one call in the auction.
        :param player: The direction making the call.
        :param bid: The call, such as "PASS", "1S", "3NT", "DBL", or "RDBL".
        """
        if self.is_bidding_over or player != self.current_bidder:
            return False

        bid_upper = bid.upper()
        if not BridgeLogic.is_legal_call(bid_upper, self.bidding_history):
            return False

        self.bidding_history.append(bid_upper)

        # The auction ends after three passes over a contract or four opening passes.
        if self._check_bidding_finished():
            self.is_bidding_over = True
            self._finalize_contract()
        else:
            self.current_bidder = PLAYER_NEXT[self.current_bidder]

        return True

    def _check_bidding_finished(self) -> bool:
        """Check whether the auction has ended."""
        h = self.bidding_history
        if len(h) == 4 and all(c == "PASS" for c in h):
            return True  # All four players passed, so the board is passed out.
        if len(h) >= 4 and all(c == "PASS" for c in h[-3:]):
            return True  # Three consecutive passes ended the auction.
        return False

    def _finalize_contract(self):
        """Set the final contract, declarer, trump suit, and opening leader."""
        last_bid = BridgeLogic.get_last_real_bid(self.bidding_history)
        if not last_bid:
            self.contract = "PASSED_OUT"
            return

        self.contract = f"{last_bid['level']}{last_bid['strain']}"
        self.trump_suit = last_bid['strain']

        # Determine the double or redouble status.
        for call in reversed(self.bidding_history):
            if call in ["DBL", "X", "DOUBLE"]:
                self.risk_status = "DOUBLE"
                break
            if call in ["RDBL", "XX", "REDOUBLE"]:
                self.risk_status = "REDOUBLE"
                break
            if call not in ["PASS", "P"]:
                break

        # Find the first player on the declaring side to bid the final strain.
        target_strain = self.trump_suit
        final_bid_index = max(
            index
            for index, call in enumerate(self.bidding_history)
            if (
                (parsed := BridgeLogic.parse_call(call))
                and parsed.get("type") == "BID"
                and parsed.get("level") == last_bid["level"]
                and parsed.get("strain") == target_strain
            )
        )
        final_bidder_index = (
            PLAYERS.index(self.dealer) + final_bid_index
        ) % 4
        for i, call in enumerate(self.bidding_history):
            parsed = BridgeLogic.parse_call(call)
            if (
                parsed
                and parsed.get("type") == "BID"
                and parsed.get("strain") == target_strain
                and (PLAYERS.index(self.dealer) + i) % 2
                == final_bidder_index % 2
            ):
                bidder_idx = (PLAYERS.index(self.dealer) + i) % 4
                self.declarer = PLAYERS[bidder_idx]
                break

        # The opening leader is the player to declarer's left.
        if self.declarer:
            self.current_player = PLAYER_NEXT[self.declarer]

    def start_play(self, contract: str, declarer: str, risk_status: str = "NONE"):
        """Initialize card play from a persisted contract and declarer."""
        parsed_contract = BridgeLogic.parse_call(contract)
        normalized_declarer = declarer.upper()
        normalized_risk = risk_status.upper()
        if not parsed_contract or parsed_contract.get("type") != "BID":
            raise ValueError(f"Invalid contract: {contract}")
        if normalized_declarer not in PLAYERS:
            raise ValueError(f"Invalid declarer: {declarer}")
        if normalized_risk not in {"NONE", "DOUBLE", "REDOUBLE"}:
            raise ValueError(f"Invalid risk status: {risk_status}")

        self.contract = f"{parsed_contract['level']}{parsed_contract['strain']}"
        self.trump_suit = parsed_contract["strain"]
        self.declarer = normalized_declarer
        self.risk_status = normalized_risk
        self.is_bidding_over = True
        self.current_player = PLAYER_NEXT[normalized_declarer]

    # ==================== Play phase ====================

    def get_legal_cards(self, player: str) -> List[str]:
        """Return the cards the specified player may legally play."""
        if not self.is_bidding_over or player != self.current_player:
            return []

        player_hand = self.hands[player]

        # 1. On lead, every card in the hand is legal.
        if not self.current_trick:
            legal = []
            for suit, ranks in player_hand.items():
                for rank in ranks:
                    legal.append(f"{suit}{rank}")
            return legal

        # 2. Follow suit when holding a card in the led suit.
        lead_suit = self.current_trick[0][1][0]
        if player_hand.get(lead_suit):
            return [f"{lead_suit}{rank}" for rank in player_hand[lead_suit]]

        # 3. When void in the led suit, any card may be discarded or trumped.
        legal = []
        for suit, ranks in player_hand.items():
            for rank in ranks:
                legal.append(f"{suit}{rank}")
        return legal

    def play_card(self, player: str, card: str) -> bool:
        """
        Play a card and advance the turn.
        :param player: The player making the play.
        :param card: The card, such as "HA" or "ST".
        """
        if card not in self.get_legal_cards(player):
            return False

        suit, rank = card[0], card[1:]
        self.hands[player][suit].remove(rank)

        if not self.current_trick:
            self.lead_suit = suit

        self.current_trick.append((player, card))

        # Once all four players have played, determine the winner and start a new trick.
        if len(self.current_trick) == 4:
            winner = self.evaluate_trick()
            self.tricks_won[winner] += 1
            self.completed_tricks.append(self.current_trick)
            self.current_trick = []
            self.lead_suit = None
            self.current_player = winner  # The trick winner leads the next trick.
        else:
            self.current_player = PLAYER_NEXT[player]

        return True

    def evaluate_trick(self) -> str:
        """Determine and return the direction that won the completed trick."""
        if len(self.current_trick) < 4:
            raise ValueError("The current trick is incomplete; fewer than four cards have been played.")

        winning_player, winning_card = self.current_trick[0]
        winning_suit, winning_rank_char = winning_card[0], winning_card[1:]
        winning_rank_val = RANKS.index(winning_rank_char)

        for player, card in self.current_trick[1:]:
            suit, rank_char = card[0], card[1:]
            rank_val = RANKS.index(rank_char)

            is_winning = False
            # 1. A trump card wins over a non-trump card.
            if suit == self.trump_suit:
                if winning_suit != self.trump_suit:
                    is_winning = True
                elif rank_val > winning_rank_val:
                    is_winning = True
            # 2. A higher card in the led suit wins unless a trump is currently winning.
            elif suit == self.lead_suit and winning_suit != self.trump_suit:
                if rank_val > winning_rank_val:
                    is_winning = True

            if is_winning:
                winning_player = player
                winning_card = card
                winning_suit = suit
                winning_rank_val = rank_val

        return winning_player

    def get_current_pbn_deal(self) -> str:
        """Build a PBN deal string for the remaining cards in DDS format."""
        # Arrange the hands in North, East, South, West order.
        hands_pbn = []
        for p in ["NORTH", "EAST", "SOUTH", "WEST"]:
            hands_pbn.append(PbnParser.hand_to_pbn(self.hands[p]))
        return "N:" + " ".join(hands_pbn)