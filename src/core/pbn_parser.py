# src/core/pbn_parser.py
from typing import Dict, List


class PbnParser:
    @staticmethod
    def parse_hand(pbn_str: str) -> Dict[str, List[str]]:
        """Parse a PBN hand string such as 'AKQ.JT9.876.543'."""
        suits_data = {'S': [], 'H': [], 'D': [], 'C': []}
        suit_keys = ['S', 'H', 'D', 'C']

        parts = pbn_str.strip().split('.')
        for i, part in enumerate(parts):
            if i < len(suit_keys):
                suit = suit_keys[i]
                suits_data[suit] = [char.upper() for char in part if char.upper() in '23456789TJQKA']
        return suits_data

    @staticmethod
    def hand_to_pbn(hand_dict: Dict[str, List[str]]) -> str:
        """Convert a hand dictionary to a PBN string."""
        suit_keys = ['S', 'H', 'D', 'C']
        parts = ["".join(hand_dict.get(suit, [])) for suit in suit_keys]
        return ".".join(parts)

    @staticmethod
    def validate_deal(hands: Dict[str, str]) -> bool:
        """Check that the four hands contain 52 distinct cards."""
        all_cards = set()
        total_count = 0
        for player, pbn in hands.items():
            parsed = PbnParser.parse_hand(pbn)
            for suit, ranks in parsed.items():
                for rank in ranks:
                    card = f"{suit}{rank}"
                    if card in all_cards:
                        return False
                    all_cards.add(card)
                    total_count += 1
        return total_count == 52