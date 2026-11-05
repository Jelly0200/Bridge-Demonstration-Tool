from copy import deepcopy
from typing import Any, Dict, List, Optional, Set


DEFAULT_COLOR_JOBS = {
    "leading": {
        "RED": "OVERRIDE_FIRST",
        "ORANGE": "FIRST",
        "YELLOW": "LAST",
        "BLUE": "LAST",
        "PURPLE": "LAST",
        "GREEN": "LAST",
    },
    "following": {
        "RED": "LAST",
        "ORANGE": "LAST",
        "YELLOW": "LAST",
        "BLUE": "FIRST",
        "PURPLE": "FIRST",
        "GREEN": "FIRST",
    },
    "discarding": {
        "RED": "LAST",
        "ORANGE": "LAST",
        "YELLOW": "LAST",
        "BLUE": "OVERRIDE_FIRST",
        "PURPLE": "FIRST",
        "GREEN": "LAST",
    },
}


class LabelEvaluator:
    PLAY_TYPES = {"leading", "following", "discarding"}
    LABEL_COLORS = {"RED", "ORANGE", "YELLOW", "BLUE", "PURPLE", "GREEN"}
    JOB_TYPES = {
        "OFF",
        "FIRST",
        "LAST",
        "OVERRIDE_FIRST",
        "OVERRIDE_LAST",
    }
    COLOR_PRIORITY = {
        "leading": ("ORANGE", "PURPLE", "BLUE", "GREEN", "YELLOW", "RED"),
        "following": ("GREEN", "BLUE", "PURPLE", "ORANGE", "RED", "YELLOW"),
        "discarding": ("PURPLE", "ORANGE", "RED", "GREEN", "YELLOW", "BLUE"),
    }
    UNLABELED_PRIORITY_INDEX = {
        "leading": 1,
        "following": 3,
        "discarding": 1,
    }

    @classmethod
    def evaluate_card_choice(
        cls,
        legal_cards: List[str],
        dds_card_scores: Dict[str, int],
        labels: List[Dict[str, Any]],
        play_type: str,
        color_jobs: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> Optional[str]:
        """Choose a legal card using the play phase's color jobs."""
        if not legal_cards:
            return None
        if play_type not in cls.PLAY_TYPES:
            raise ValueError(f"Unsupported play type: {play_type}")

        jobs = cls.normalize_color_jobs(color_jobs)
        scores = {
            card: dds_card_scores[card]
            for card in legal_cards
            if card in dds_card_scores
        }
        best_cards = cls._best_cards(legal_cards, scores)
        unlabeled_cards = cls._unlabeled_cards(labels, legal_cards)
        priority = cls.COLOR_PRIORITY[play_type]
        phase_jobs = jobs[play_type]

        for color in priority:
            job = phase_jobs[color]
            if job.startswith("OVERRIDE_"):
                selected = cls._first_labeled_card(
                    labels,
                    color,
                    legal_cards,
                    descending=job.endswith("LAST"),
                )
                if selected:
                    return selected

        preference = list(priority)
        preference.insert(cls.UNLABELED_PRIORITY_INDEX[play_type], None)
        for color in preference:
            if color is None:
                selected = cls._first_card_in(
                    legal_cards,
                    best_cards & unlabeled_cards,
                )
                if selected:
                    return selected
                continue

            job = phase_jobs[color]
            if job not in {"FIRST", "LAST"}:
                continue
            selected = cls._first_labeled_card(
                labels,
                color,
                best_cards,
                descending=job == "LAST",
            )
            if selected:
                return selected
        return None

    @classmethod
    def normalize_color_jobs(
        cls,
        color_jobs: Optional[Dict[str, Dict[str, str]]],
    ) -> Dict[str, Dict[str, str]]:
        jobs = deepcopy(DEFAULT_COLOR_JOBS)
        if color_jobs is None:
            return jobs
        for play_type, phase_jobs in color_jobs.items():
            if play_type not in cls.PLAY_TYPES:
                raise ValueError(f"Unsupported play type: {play_type}")
            for color, job in phase_jobs.items():
                normalized_color = color.upper()
                if normalized_color not in cls.LABEL_COLORS:
                    raise ValueError(f"Unsupported label color: {color}")
                if job not in cls.JOB_TYPES:
                    raise ValueError(f"Unsupported label job: {job}")
                jobs[play_type][normalized_color] = job
        return jobs

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
    def _first_labeled_card(
        labels: List[Dict[str, Any]],
        color: str,
        candidates: List[str] | Set[str],
        descending: bool = False,
    ) -> Optional[str]:
        candidate_cards = set(candidates)
        ordered_labels = sorted(
            (
                label for label in labels
                if label.get("Color", "").upper() == color
            ),
            key=lambda label: (
                -label.get("Sequence", 999)
                if descending
                else label.get("Sequence", 999)
            ),
        )
        for label in ordered_labels:
            card = label.get("Card", "").upper()
            if card in candidate_cards:
                return card
        return None

    @classmethod
    def _unlabeled_cards(
        cls,
        labels: List[Dict[str, Any]],
        cards: List[str],
    ) -> Set[str]:
        labeled_cards = {
            label.get("Card", "").upper()
            for label in labels
            if label.get("Color", "").upper() in cls.LABEL_COLORS
        }
        return set(cards) - labeled_cards
