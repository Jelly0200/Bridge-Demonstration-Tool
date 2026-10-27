import unittest

from src.robot.label_evaluator import LabelEvaluator


class TestLabelEvaluator(unittest.TestCase):
    @staticmethod
    def choose(legal_cards, scores, labels, play_type):
        return LabelEvaluator.evaluate_card_choice(
            legal_cards=legal_cards,
            dds_card_scores=scores,
            labels=labels,
            play_type=play_type,
        )

    def test_red_leads_precede_all_other_options_in_ascending_sequence(self):
        labels = [
            {"Sequence": 2, "Color": "RED", "Card": "SA"},
            {"Sequence": 1, "Color": "RED", "Card": "SK"},
            {"Sequence": 1, "Color": "ORANGE", "Card": "SQ"},
        ]
        self.assertEqual(
            self.choose(
                ["SA", "SK", "SQ"],
                {"SA": 9, "SK": 8, "SQ": 10},
                labels,
                "leading",
            ),
            "SK",
        )

    def test_orange_leads_use_ascending_sequence_in_best_group(self):
        labels = [
            {"Sequence": 2, "Color": "ORANGE", "Card": "SA"},
            {"Sequence": 1, "Color": "ORANGE", "Card": "SK"},
        ]
        self.assertEqual(
            self.choose(
                ["SA", "SK", "SQ"],
                {"SA": 9, "SK": 9, "SQ": 8},
                labels,
                "leading",
            ),
            "SK",
        )
        self.assertEqual(
            self.choose(
                ["SA", "SK"],
                {"SA": 7, "SK": 9},
                labels,
                "leading",
            ),
            "SK",
        )

    def test_unlabeled_best_lead_precedes_best_blue_purple_and_green(self):
        labels = [{"Sequence": 1, "Color": "BLUE", "Card": "SQ"}]
        self.assertEqual(
            self.choose(
                ["SA", "SK", "SQ"],
                {"SK": 9, "SQ": 9},
                labels,
                "leading",
            ),
            "SK",
        )

    def test_best_lead_labels_use_the_documented_color_order(self):
        labels = [
            {"Sequence": 1, "Color": "BLUE", "Card": "SA"},
            {"Sequence": 3, "Color": "BLUE", "Card": "SK"},
            {"Sequence": 10, "Color": "PURPLE", "Card": "SQ"},
            {"Sequence": 20, "Color": "GREEN", "Card": "SJ"},
        ]
        self.assertEqual(
            self.choose(
                ["SA", "SK", "SQ", "SJ"],
                {card: 9 for card in ("SA", "SK", "SQ", "SJ")},
                labels,
                "leading",
            ),
            "SQ",
        )

    def test_best_orange_lead_precedes_unlabeled_and_other_best_labels(self):
        labels = [
            {"Sequence": 1, "Color": "ORANGE", "Card": "SA"},
            {"Sequence": 1, "Color": "PURPLE", "Card": "SK"},
        ]
        self.assertEqual(
            self.choose(
                ["SA", "SK", "SQ"],
                {"SA": 9, "SK": 9, "SQ": 9},
                labels,
                "leading",
            ),
            "SA",
        )

    def test_best_lead_order_is_orange_uncolored_purple_blue_green(self):
        labels = [
            {"Sequence": 1, "Color": "ORANGE", "Card": "SA"},
            {"Sequence": 1, "Color": "PURPLE", "Card": "SK"},
            {"Sequence": 1, "Color": "BLUE", "Card": "SQ"},
            {"Sequence": 1, "Color": "GREEN", "Card": "SJ"},
        ]
        cards = ["SA", "SK", "SQ", "SJ", "ST"]
        scores = {card: 9 for card in cards}

        self.assertEqual(
            self.choose(cards, scores, labels, "leading"),
            "SA",
        )
        labels = [label for label in labels if label["Color"] != "ORANGE"]
        labels.append({"Sequence": 1, "Color": "YELLOW", "Card": "SA"})
        self.assertEqual(
            self.choose(cards, scores, labels, "leading"),
            "ST",
        )
        labels.append({"Sequence": 1, "Color": "YELLOW", "Card": "ST"})
        self.assertEqual(
            self.choose(cards, scores, labels, "leading"),
            "SK",
        )

    def test_nonbest_lead_labels_are_ignored_when_dds_best_is_uncolored(self):
        labels = [
            {"Sequence": 1, "Color": "ORANGE", "Card": "SA"},
            {"Sequence": 1, "Color": "PURPLE", "Card": "SK"},
        ]
        self.assertEqual(
            self.choose(
                ["SA", "SK", "SQ"],
                {"SQ": 9, "SA": 8, "SK": 7},
                labels,
                "leading",
            ),
            "SQ",
        )

    def test_yellow_best_lead_precedes_all_nonbest_cards(self):
        labels = [{"Sequence": 10, "Color": "YELLOW", "Card": "SQ"}]
        self.assertEqual(
            self.choose(
                ["SA", "SK", "SQ"],
                {"SQ": 9, "SA": 8, "SK": 7},
                labels,
                "leading",
            ),
            "SQ",
        )

    def test_leading_returns_none_when_dds_has_no_best_group(self):
        labels = [
            {"Sequence": 1, "Color": "YELLOW", "Card": "SA"},
            {"Sequence": 10, "Color": "YELLOW", "Card": "SK"},
        ]
        self.assertIsNone(self.choose(["SA", "SK"], {}, labels, "leading"))

    def test_blue_discard_is_unconditional_and_ascending(self):
        labels = [
            {"Sequence": 2, "Color": "BLUE", "Card": "SA"},
            {"Sequence": 1, "Color": "BLUE", "Card": "SK"},
        ]
        self.assertEqual(
            self.choose(
                ["SA", "SK"],
                {"SA": 9, "SK": 8},
                labels,
                "discarding",
            ),
            "SK",
        )

    def test_purple_best_discard_uses_ascending_sequence(self):
        labels = [
            {"Sequence": 2, "Color": "PURPLE", "Card": "SA"},
            {"Sequence": 1, "Color": "PURPLE", "Card": "SK"},
        ]
        self.assertEqual(
            self.choose(
                ["SA", "SK", "SQ"],
                {"SA": 9, "SK": 9, "SQ": 8},
                labels,
                "discarding",
            ),
            "SK",
        )

    def test_unlabeled_best_discard_precedes_red_and_orange_best_discards(self):
        labels = [
            {"Sequence": 1, "Color": "RED", "Card": "SA"},
            {"Sequence": 1, "Color": "ORANGE", "Card": "SQ"},
        ]
        self.assertEqual(
            self.choose(
                ["SA", "SK", "SQ"],
                {"SA": 9, "SK": 10, "SQ": 10},
                labels,
                "discarding",
            ),
            "SK",
        )

    def test_best_orange_then_red_discards_use_descending_sequence(self):
        labels = [
            {"Sequence": 1, "Color": "RED", "Card": "SA"},
            {"Sequence": 3, "Color": "RED", "Card": "SK"},
            {"Sequence": 10, "Color": "ORANGE", "Card": "SQ"},
        ]
        self.assertEqual(
            self.choose(
                ["SA", "SK", "SQ"],
                {"SA": 9, "SK": 9, "SQ": 9},
                labels,
                "discarding",
            ),
            "SQ",
        )

    def test_best_green_discards_use_descending_sequence(self):
        labels = [
            {"Sequence": 1, "Color": "GREEN", "Card": "SA"},
            {"Sequence": 3, "Color": "GREEN", "Card": "SK"},
        ]
        self.assertEqual(
            self.choose(
                ["SA", "SK"],
                {"SA": 9, "SK": 9},
                labels,
                "discarding",
            ),
            "SK",
        )

    def test_best_discard_labels_follow_the_documented_color_order(self):
        labels = [
            {"Sequence": 1, "Color": "RED", "Card": "SK"},
            {"Sequence": 1, "Color": "PURPLE", "Card": "SJ"},
            {"Sequence": 10, "Color": "YELLOW", "Card": "SQ"},
        ]
        self.assertEqual(
            self.choose(
                ["SA", "SK", "SQ", "SJ"],
                {card: 9 for card in ("SA", "SK", "SQ", "SJ")},
                labels,
                "discarding",
            ),
            "SJ",
        )

    def test_uncolored_best_discard_precedes_orange_red_and_green(self):
        labels = [
            {"Sequence": 1, "Color": "ORANGE", "Card": "SK"},
            {"Sequence": 1, "Color": "RED", "Card": "SQ"},
            {"Sequence": 1, "Color": "GREEN", "Card": "SJ"},
        ]
        self.assertEqual(
            self.choose(
                ["SK", "SQ", "SJ", "SA"],
                {card: 9 for card in ("SK", "SQ", "SJ", "SA")},
                labels,
                "discarding",
            ),
            "SA",
        )

    def test_discarding_returns_none_when_dds_has_no_best_group(self):
        labels = [
            {"Sequence": 1, "Color": "YELLOW", "Card": "SA"},
            {"Sequence": 10, "Color": "YELLOW", "Card": "SK"},
        ]
        self.assertIsNone(self.choose(["SA", "SK"], {}, labels, "discarding"))

    def test_yellow_is_selected_only_when_it_is_dds_best(self):
        labels = [
            {"Sequence": 1, "Color": "YELLOW", "Card": "H8"},
            {"Sequence": 10, "Color": "YELLOW", "Card": "H9"},
            {"Sequence": 1, "Color": "GREEN", "Card": "HT"},
        ]
        self.assertEqual(
            self.choose(
                ["H8", "H9", "HT"],
                {"H8": 9, "H9": 9, "HT": 8},
                labels,
                "following",
            ),
            "H9",
        )

    def test_green_best_following_cards_precede_other_colors_ascending(self):
        labels = [
            {"Sequence": 2, "Color": "GREEN", "Card": "H8"},
            {"Sequence": 1, "Color": "GREEN", "Card": "H9"},
            {"Sequence": 10, "Color": "YELLOW", "Card": "HT"},
        ]
        self.assertEqual(
            self.choose(
                ["H8", "H9", "HT"],
                {"H8": 10, "H9": 10, "HT": 9},
                labels,
                "following",
            ),
            "H9",
        )

    def test_best_non_yellow_following_card_precedes_yellow_fallback(self):
        labels = [
            {"Sequence": 10, "Color": "YELLOW", "Card": "H8"},
            {"Sequence": 1, "Color": "YELLOW", "Card": "HT"},
        ]
        self.assertEqual(
            self.choose(
                ["H8", "H9", "HT"],
                {"H8": 8, "H9": 9, "HT": 8},
                labels,
                "following",
            ),
            "H9",
        )

    def test_following_best_group_uses_blue_purple_uncolored_orange_red_order(self):
        labels = [
            {"Sequence": 1, "Color": "BLUE", "Card": "H8"},
            {"Sequence": 1, "Color": "PURPLE", "Card": "H9"},
            {"Sequence": 1, "Color": "ORANGE", "Card": "HT"},
            {"Sequence": 1, "Color": "RED", "Card": "HJ"},
        ]
        cards = ["H8", "H9", "HT", "HJ", "HQ"]
        scores = {card: 9 for card in cards}

        self.assertEqual(
            self.choose(cards, scores, labels, "following"),
            "H8",
        )
        labels = [label for label in labels if label["Color"] != "BLUE"]
        labels.append({"Sequence": 1, "Color": "YELLOW", "Card": "H8"})
        self.assertEqual(
            self.choose(cards, scores, labels, "following"),
            "H9",
        )
        labels = [label for label in labels if label["Color"] != "PURPLE"]
        labels.append({"Sequence": 1, "Color": "YELLOW", "Card": "H9"})
        self.assertEqual(
            self.choose(cards, scores, labels, "following"),
            "HQ",
        )

    def test_following_ignores_nonbest_cards_and_returns_none_without_dds(self):
        labels = [
            {"Sequence": 1, "Color": "BLUE", "Card": "H8"},
            {"Sequence": 1, "Color": "PURPLE", "Card": "H9"},
            {"Sequence": 1, "Color": "ORANGE", "Card": "HT"},
            {"Sequence": 1, "Color": "RED", "Card": "HJ"},
            {"Sequence": 1, "Color": "YELLOW", "Card": "HQ"},
        ]
        self.assertIsNone(
            self.choose(
                ["H8", "H9", "HT", "HJ", "HQ"],
                {},
                labels,
                "following",
            )
        )

    def test_following_returns_none_when_dds_has_no_best_group(self):
        labels = [
            {"Sequence": 1, "Color": "YELLOW", "Card": "H8"},
            {"Sequence": 10, "Color": "YELLOW", "Card": "H9"},
        ]
        self.assertIsNone(self.choose(["H8", "H9"], {}, labels, "following"))

    def test_label_priorities_apply_only_to_their_defined_play_phase(self):
        labels = [{"Sequence": 1, "Color": "RED", "Card": "SA"}]
        self.assertEqual(
            self.choose(["SA", "SK"], {"SA": 7, "SK": 9}, labels, "following"),
            "SK",
        )
        self.assertEqual(
            self.choose(["SA", "SK"], {"SA": 7, "SK": 9}, labels, "discarding"),
            "SK",
        )

    def test_nonbest_label_cards_are_never_selected(self):
        labels = [{"Sequence": 1, "Color": "GREEN", "Card": "SA"}]
        self.assertEqual(
            self.choose(["SA", "SK"], {"SA": 8, "SK": 9}, labels, "leading"),
            "SK",
        )
        self.assertEqual(
            self.choose(["SA", "SK"], {"SA": 8, "SK": 9}, labels, "following"),
            "SK",
        )
        labels = [{"Sequence": 1, "Color": "PURPLE", "Card": "SA"}]
        self.assertEqual(
            self.choose(
                ["SA", "SK"],
                {"SA": 8, "SK": 9},
                labels,
                "discarding",
            ),
            "SK",
        )

    def test_returns_none_when_no_cards_are_legal(self):
        self.assertIsNone(self.choose([], {}, [], "leading"))

    def test_rejects_unknown_play_type(self):
        with self.assertRaises(ValueError):
            self.choose(["SA"], {}, [], "unknown")


if __name__ == "__main__":
    unittest.main()
