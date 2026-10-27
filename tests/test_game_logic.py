import unittest

from src.core.bridge_game import BridgeGameEngine
from src.core.pbn_parser import PbnParser


class TestGameLogic(unittest.TestCase):
    def setUp(self):
        self.hands = {
            "NORTH": "AKQJ.T98.765.432",
            "EAST": "432.AKQJ.T98.765",
            "SOUTH": "T98.765.AKQJ.T98",
            "WEST": "765.432.432.AKQJ",
        }

    def test_pbn_parsing_and_round_trip(self):
        pbn = "AKQ.JT9.876.543"
        parsed = PbnParser.parse_hand(pbn)

        self.assertEqual(parsed["S"], ["A", "K", "Q"])
        self.assertEqual(parsed["H"], ["J", "T", "9"])
        self.assertEqual(PbnParser.hand_to_pbn(parsed), pbn)

    def test_deal_validation_rejects_duplicate_cards(self):
        duplicate_deal = {
            "NORTH": "AKQJ.T98.765.432",
            "EAST": "AKQJ.T98.765.432",
            "SOUTH": "T98.765.AKQJ.T98",
            "WEST": "765.432.432.AKQJ",
        }

        self.assertFalse(PbnParser.validate_deal(duplicate_deal))

    def test_auction_initializes_play_and_enforces_follow_suit(self):
        game = BridgeGameEngine(self.hands, dealer="SOUTH", vulnerability="NONE")
        self.assertTrue(game.make_bid("SOUTH", "1NT"))
        self.assertTrue(game.make_bid("WEST", "PASS"))
        self.assertTrue(game.make_bid("NORTH", "PASS"))
        self.assertTrue(game.make_bid("EAST", "PASS"))

        self.assertEqual(game.contract, "1NT")
        self.assertEqual(game.declarer, "SOUTH")
        self.assertEqual(game.current_player, "WEST")

        west_legal_cards = game.get_legal_cards("WEST")
        self.assertEqual(len(west_legal_cards), 13)
        self.assertEqual(game.get_legal_cards("SOUTH"), [])

        lead_card = west_legal_cards[0]
        self.assertTrue(game.play_card("WEST", lead_card))
        north_legal_cards = game.get_legal_cards("NORTH")
        self.assertTrue(north_legal_cards)
        self.assertTrue(all(card.startswith(lead_card[0]) for card in north_legal_cards))

    def test_declarer_is_first_partner_to_bid_final_strain(self):
        game = BridgeGameEngine(self.hands, dealer="SOUTH")
        auction = (
            ("SOUTH", "1C"),
            ("WEST", "1H"),
            ("NORTH", "2H"),
            ("EAST", "PASS"),
            ("SOUTH", "PASS"),
            ("WEST", "PASS"),
        )

        for player, call in auction:
            self.assertTrue(game.make_bid(player, call))

        self.assertEqual(game.contract, "2H")
        self.assertEqual(game.declarer, "NORTH")
        self.assertEqual(game.current_player, "EAST")

    def test_completed_trick_awards_lead_to_winner(self):
        game = BridgeGameEngine(self.hands, dealer="SOUTH")
        for player, call in (
            ("SOUTH", "1NT"),
            ("WEST", "PASS"),
            ("NORTH", "PASS"),
            ("EAST", "PASS"),
        ):
            self.assertTrue(game.make_bid(player, call))

        for _ in range(4):
            player = game.current_player
            if player is None:
                self.fail("The game did not assign a player to lead the next card.")
            legal_cards = game.get_legal_cards(player)
            if not legal_cards:
                self.fail(f"Player {player} has no legal card during the trick.")
            self.assertTrue(game.play_card(player, legal_cards[0]))

        self.assertEqual(len(game.completed_tricks), 1)
        self.assertEqual(sum(game.tricks_won.values()), 1)
        winner = game.current_player
        if winner is None:
            self.fail("The completed trick did not assign the next leader.")
        self.assertEqual(game.tricks_won[winner], 1)

    def test_start_play_initializes_persisted_contract(self):
        game = BridgeGameEngine(self.hands, dealer="SOUTH")

        game.start_play("3NT", "NORTH", "DOUBLE")

        self.assertEqual(game.contract, "3NT")
        self.assertEqual(game.trump_suit, "NT")
        self.assertEqual(game.declarer, "NORTH")
        self.assertEqual(game.risk_status, "DOUBLE")
        self.assertTrue(game.is_bidding_over)
        self.assertEqual(game.current_player, "EAST")
        self.assertTrue(game.get_legal_cards("EAST"))

    def test_start_play_rejects_invalid_persisted_contract(self):
        game = BridgeGameEngine(self.hands)

        with self.assertRaises(ValueError):
            game.start_play("PASS", "SOUTH")
        with self.assertRaises(ValueError):
            game.start_play("4H", "NORTHEAST")


if __name__ == "__main__":
    unittest.main()
