# src/core/bridge_logic.py
from typing import List, Optional, Union, Dict, Any


class BridgeLogic:
    # Define the ascending weights for bid strains.
    STRAIN_RANK = {
        'C': 1,
        'D': 2,
        'H': 3,
        'S': 4,
        'NT': 5
    }

    @staticmethod
    def parse_call(call_str: str) -> Optional[Dict[str, Any]]:
        """
        Parse a call such as "1S", "3NT", "PASS", "DBL", or "RDBL".
        Return a structured dictionary or None for an invalid call.
        """
        call_upper = call_str.strip().upper()

        if call_upper in ["PASS", "P"]:
            return {"type": "PASS"}
        if call_upper in ["DBL", "X", "DOUBLE"]:
            return {"type": "DOUBLE"}
        if call_upper in ["RDBL", "XX", "REDOUBLE"]:
            return {"type": "REDOUBLE"}

        # Parse a standard contract bid such as "1S" or "3NT".
        if len(call_upper) < 2:
            return None

        try:
            level = int(call_upper[0])
            strain = call_upper[1:]
            if level < 1 or level > 7:
                return None
            if strain not in BridgeLogic.STRAIN_RANK:
                return None
            return {
                "type": "BID",
                "level": level,
                "strain": strain,
                "rank_value": level * 5 + BridgeLogic.STRAIN_RANK[strain]
            }
        except ValueError:
            return None

    @classmethod
    def get_last_real_bid(cls, bidding_history: List[str]) -> Optional[Dict[str, Any]]:
        """Find the most recent contract bid in the auction history."""
        for call in reversed(bidding_history):
            parsed = cls.parse_call(call)
            if parsed and parsed["type"] == "BID":
                return parsed
        return None

    @classmethod
    def is_legal_call(cls, call_to_check: str, bidding_history: List[str]) -> bool:
        """
        Check whether a call is legal:
        1. PASS is always legal.
        2. DOUBLE is allowed after an undoubled contract bid (partially simplified).
        3. REDOUBLE is allowed after a DOUBLE.
        4. A contract bid must outrank the highest previous contract bid.
        """
        parsed_call = cls.parse_call(call_to_check)
        if not parsed_call:
            return False

        call_type = parsed_call["type"]

        # PASS is always legal.
        if call_type == "PASS":
            return True

        # Find the latest contract bid.
        last_bid = cls.get_last_real_bid(bidding_history)

        # Check whether DOUBLE is legal.
        if call_type == "DOUBLE":
            if not last_bid:
                return False
            # This simplified check only verifies that the latest non-pass action was a bid.
            # Full validation also requires that the bid came from the opposing partnership.
            recent_calls = [cls.parse_call(c) for c in reversed(bidding_history) if cls.parse_call(c)]
            # Ignore consecutive passes when finding the latest action.
            non_pass_calls = [c for c in recent_calls if c["type"] != "PASS"]
            if not non_pass_calls:
                return False
            last_action = non_pass_calls[0]["type"]
            # A bid as the latest non-pass action permits a double in this simplified model.
            return last_action == "BID"

        # Check whether REDOUBLE is legal.
        if call_type == "REDOUBLE":
            recent_calls = [cls.parse_call(c) for c in reversed(bidding_history) if cls.parse_call(c)]
            non_pass_calls = [c for c in recent_calls if c["type"] != "PASS"]
            if not non_pass_calls:
                return False
            # A double as the latest non-pass action permits a redouble.
            return non_pass_calls[0]["type"] == "DOUBLE"

        # Check whether a standard contract bid is legal.
        if call_type == "BID":
            if not last_bid:
                return True  # Any contract bid may open an auction with no previous bids.
            # The new contract bid must outrank the previous contract bid.
            return parsed_call["rank_value"] > last_bid["rank_value"]

        return False

    @classmethod
    def get_legal_bids(cls, bidding_history: List[str]) -> List[str]:
        """Return all calls considered legal for the current auction."""
        legal_calls = ["PASS", "DBL", "RDBL"]

        # Generate all standard contract bids from 1C through 7NT.
        levels = range(1, 8)
        strains = ["C", "D", "H", "S", "NT"]

        possible_bids = []
        for lvl in levels:
            for st in strains:
                possible_bids.append(f"{lvl}{st}")

        # Filter the calls against the current auction history.
        valid_options = []

        # Validate each possible contract bid.
        for call in possible_bids:
            if cls.is_legal_call(call, bidding_history):
                valid_options.append(call)

        # Check whether DOUBLE and REDOUBLE are legal.
        if cls.is_legal_call("DBL", bidding_history):
            valid_options.append("DBL")
        if cls.is_legal_call("RDBL", bidding_history):
            valid_options.append("RDBL")

        # PASS is always legal.
        valid_options.append("PASS")

        return valid_options