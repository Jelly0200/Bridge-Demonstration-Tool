from typing import Any, Dict, List, Optional, Set


class LabelEvaluator:
    PLAY_TYPES = {"leading", "following", "discarding"}
    LABEL_COLORS = {"RED", "ORANGE", "YELLOW", "BLUE", "PURPLE", "GREEN"}

    @staticmethod
    def evaluate_card_choice(
        legal_cards: List[str],
        dds_card_scores: Dict[str, int],
        labels: List[Dict[str, Any]],
        play_type: str,
    ) -> Optional[str]:
        """Choose one legal card according to the play phase and label priority."""
        if not legal_cards:
            return None
        if play_type not in LabelEvaluator.PLAY_TYPES:
            raise ValueError(f"Unsupported play type: {play_type}")

        scores = {
            card: dds_card_scores[card]
            for card in legal_cards
            if card in dds_card_scores
        }
        best_cards = LabelEvaluator._best_cards(legal_cards, scores)
        unlabeled_cards = LabelEvaluator._unlabeled_cards(labels, legal_cards)

        if play_type == "leading":
            selected = LabelEvaluator._first_labeled_card(
                labels,
                {"RED"},
                legal_cards,
            )
            if selected:
                return selected

            preference = (
                ("ORANGE", False),
                (None, False),
                ("PURPLE", True),
                ("BLUE", True),
                ("GREEN", True),
                ("YELLOW", True),
            )
            return LabelEvaluator._first_by_preference(
                labels,
                legal_cards,
                best_cards,
                unlabeled_cards,
                preference,
            )

        if play_type == "following":
            preference = (
                ("GREEN", False),
                ("BLUE", False),
                ("PURPLE", False),
                (None, False),
                ("ORANGE", True),
                ("RED", True),
                ("YELLOW", True),
            )
            return LabelEvaluator._first_by_preference(
                labels,
                legal_cards,
                best_cards,
                unlabeled_cards,
                preference,
            )

        selected = LabelEvaluator._first_labeled_card(
            labels,
            {"BLUE"},
            legal_cards,
        )
        if selected:
            return selected

        preference = (
            ("PURPLE", False),
            (None, False),
            ("ORANGE", True),
            ("RED", True),
            ("GREEN", True),
            ("YELLOW", True),
        )
        return LabelEvaluator._first_by_preference(
            labels,
            legal_cards,
            best_cards,
            unlabeled_cards,
            preference,
        )

    @staticmethod
    def _best_cards(
        legal_cards: List[str],
        scores: Dict[str, int],
    ) -> Set[str]:
        if not scores:
            return set()
        best_score = max(scores.values())
        return {
            card for card in legal_cards
            if scores.get(card) == best_score
        }

    @staticmethod
    def _first_card_in(cards: List[str], candidates: Set[str]) -> Optional[str]:
        return next((card for card in cards if card in candidates), None)

    @staticmethod
    def _first_by_preference(
        labels: List[Dict[str, Any]],
        legal_cards: List[str],
        candidates: Set[str],
        unlabeled_cards: Set[str],
        preference: tuple[tuple[Optional[str], bool], ...],
    ) -> Optional[str]:
        for color, descending in preference:
            if color is None:
                selected = LabelEvaluator._first_card_in(
                    legal_cards,
                    candidates & unlabeled_cards,
                )
            else:
                selected = LabelEvaluator._first_labeled_card(
                    labels,
                    {color},
                    candidates,
                    descending=descending,
                )
            if selected:
                return selected
        return None

    @staticmethod
    def _first_labeled_card(
        labels: List[Dict[str, Any]],
        colors: Set[str],
        candidates: List[str] | Set[str],
        descending: bool = False,
        color_order: tuple[str, ...] = (),
    ) -> Optional[str]:
        candidate_cards = set(candidates)
        color_priority = {
            color: index for index, color in enumerate(color_order)
        }
        ordered_labels = sorted(
            (
                label for label in labels
                if label.get("Color", "").upper() in colors
            ),
            key=lambda label: (
                color_priority.get(label.get("Color", "").upper(), 0),
                (
                    -label.get("Sequence", 999)
                    if descending
                    else label.get("Sequence", 999)
                ),
            ),
        )
        for label in ordered_labels:
            card = label.get("Card", "").upper()
            if card in candidate_cards:
                return card
        return None

    @staticmethod
    def _unlabeled_cards(
        labels: List[Dict[str, Any]],
        cards: List[str],
    ) -> Set[str]:
        labeled_cards = {
            label.get("Card", "").upper()
            for label in labels
            if label.get("Color", "").upper() in LabelEvaluator.LABEL_COLORS
        }
        return set(cards) - labeled_cards
