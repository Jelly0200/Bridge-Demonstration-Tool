import random
import sqlite3

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config.constants import RANKS
from src.core.pbn_parser import PbnParser
from src.database.repository import Repository
from src.ui.i18n import show_message
from src.ui.widgets.hand_widget import HandWidget


class BoardEditorDialog(QDialog):
    """Create or edit a complete board using PBN or card-by-card assignment."""

    SEATS = ("SOUTH", "WEST", "NORTH", "EAST")
    SUITS = ("S", "H", "D", "C")
    SUIT_SYMBOLS = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}
    SEAT_COLORS = {
        "SOUTH": "#1d4ed8",
        "WEST": "#15803d",
        "NORTH": "#7e22ce",
        "EAST": "#b45309",
    }
    RANKS_HIGH_TO_LOW = tuple(reversed(RANKS))

    def __init__(
        self,
        case_id: int | None = None,
        board_id: int | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.repo = Repository()
        self.board = self.repo.get_board_by_id(board_id) if board_id else None
        if board_id and self.board is None:
            raise LookupError(f"Board {board_id} was not found.")
        self.case_id = self.board.case_id if self.board else case_id
        if self.case_id is None:
            raise ValueError("A case must be selected before creating a board.")
        self.card_assignments: dict[str, str] = {}
        self.card_buttons = {}
        self.pbn_inputs = {}
        self.pbn_hand_previews = {}
        self.saved_board_id = None
        self.setWindowTitle(
            "Edit board" if self.board else "New board"
        )
        self.resize(1020, 700)
        self._init_ui()
        self._load_board()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        pbn_tab = QWidget()
        pbn_layout = QVBoxLayout(pbn_tab)
        pbn_layout.addWidget(
            QLabel(
                "Enter one PBN hand per direction. Use S.H.D.C order, "
                "for example AKQJ.T98.765.432."
            )
        )
        hand_form = QFormLayout()
        for seat in self.SEATS:
            hand_input = QLineEdit()
            hand_input.setPlaceholderText("AKQJ.T98.765.432")
            hand_input.textChanged.connect(self._update_validation)
            hand_input.textChanged.connect(
                lambda _text, direction=seat: self._update_pbn_preview(direction)
            )
            self.pbn_inputs[seat] = hand_input
            hand_form.addRow(f"{seat}:", hand_input)
            preview = HandWidget("NORTH", pbn_tab)
            self.pbn_hand_previews[seat] = preview
            hand_form.addRow(preview)
        pbn_layout.addLayout(hand_form)
        self.pbn_validation_label = QLabel("Enter all 52 cards to validate the deal.")
        self.pbn_validation_label.setWordWrap(True)
        pbn_layout.addWidget(self.pbn_validation_label)
        pbn_layout.addStretch()
        self.tabs.addTab(pbn_tab, "PBN input")

        picker_tab = QWidget()
        picker_layout = QVBoxLayout(picker_tab)
        picker_layout.addWidget(
            QLabel(
                "Choose a seat, then click cards to assign or unassign them. "
                "Each seat must receive exactly 13 cards."
            )
        )
        assignment_layout = QHBoxLayout()
        self.selected_seat_combo = QComboBox()
        self.selected_seat_combo.addItems(self.SEATS)
        self.selected_seat_combo.currentTextChanged.connect(
            self._refresh_picker_buttons
        )
        assignment_layout.addWidget(QLabel("Assign cards to:"))
        assignment_layout.addWidget(self.selected_seat_combo)
        self.btn_randomize = QPushButton("Randomize remaining cards")
        self.btn_randomize.setToolTip(
            "Randomly deal the unassigned cards when each seat has 0 or 13 cards."
        )
        self.btn_randomize.clicked.connect(self._randomize_remaining_cards)
        assignment_layout.addWidget(self.btn_randomize)
        assignment_layout.addStretch()
        picker_layout.addLayout(assignment_layout)
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(QLabel("Seat colors:"))
        self.seat_color_legend = {}
        for seat in self.SEATS:
            seat_badge = QLabel(seat)
            seat_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            seat_badge.setStyleSheet(
                f"background-color: {self.SEAT_COLORS[seat]}; color: #ffffff; "
                "border: 1px solid #e2e8f0; border-radius: 5px; "
                "font-weight: bold; padding: 5px 12px;"
            )
            legend_layout.addWidget(seat_badge)
            self.seat_color_legend[seat] = seat_badge
        legend_layout.addStretch()
        picker_layout.addLayout(legend_layout)

        card_grid = QGridLayout()
        card_grid.setSpacing(3)
        card_grid.addWidget(QLabel("Suit"), 0, 0)
        for column, rank in enumerate(self.RANKS_HIGH_TO_LOW, start=1):
            card_grid.addWidget(QLabel(rank), 0, column, Qt.AlignmentFlag.AlignCenter)
        for row, suit in enumerate(self.SUITS, start=1):
            suit_label = QLabel(self.SUIT_SYMBOLS[suit])
            suit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_grid.addWidget(suit_label, row, 0)
            for column, rank in enumerate(self.RANKS_HIGH_TO_LOW, start=1):
                card_code = f"{suit}{rank}"
                button = QPushButton(f"{rank}{self.SUIT_SYMBOLS[suit]}")
                button.setFixedSize(48, 34)
                button.setToolTip(card_code)
                button.clicked.connect(
                    lambda _checked=False, code=card_code: self._toggle_card(code)
                )
                self.card_buttons[card_code] = button
                card_grid.addWidget(button, row, column)
        picker_layout.addLayout(card_grid)

        self.picker_counts_label = QLabel()
        self.picker_counts_label.setWordWrap(True)
        picker_layout.addWidget(self.picker_counts_label)
        self.picker_validation_label = QLabel()
        self.picker_validation_label.setWordWrap(True)
        picker_layout.addWidget(self.picker_validation_label)
        picker_layout.addStretch()
        self.tabs.addTab(picker_tab, "Visual card picker")
        layout.addWidget(self.tabs)

        self.dealer_combo = QComboBox()
        self.dealer_combo.addItems(self.SEATS)
        self.vulnerability_combo = QComboBox()
        self.vulnerability_combo.addItems(["NONE", "NS", "EW", "BOTH"])
        self.description_input = QLineEdit()
        details = QFormLayout()
        details.addRow("Dealer:", self.dealer_combo)
        details.addRow("Vulnerability:", self.vulnerability_combo)
        self.description_input.setPlaceholderText("Optional board name")
        details.addRow("Board name:", self.description_input)
        layout.addLayout(details)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.btn_save = QPushButton("Save board")
        self.btn_save.clicked.connect(self.save_board)
        buttons.addWidget(self.btn_save)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        buttons.addWidget(self.btn_cancel)
        layout.addLayout(buttons)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self._update_validation()

    def _load_board(self):
        if not self.board:
            self._refresh_picker_buttons()
            return

        configuration = self.repo.get_board_configuration(
            self.board.board_configuration_id
        )
        if configuration is None:
            raise LookupError(
                f"Configuration {self.board.board_configuration_id} was not found."
            )
        hands = {
            "SOUTH": self.board.south_hand_pbn,
            "WEST": self.board.west_hand_pbn,
            "NORTH": self.board.north_hand_pbn,
            "EAST": self.board.east_hand_pbn,
        }
        for seat, hand in hands.items():
            self.pbn_inputs[seat].setText(hand)
            for suit, ranks in PbnParser.parse_hand(hand).items():
                for rank in ranks:
                    self.card_assignments[f"{suit}{rank}"] = seat

        self.dealer_combo.setCurrentText(configuration.dealer)
        self.vulnerability_combo.setCurrentText(configuration.vulnerability)
        self.description_input.setText(self.board.description or "")
        self._refresh_picker_buttons()
        self._update_validation()

    @classmethod
    def _validate_hands(cls, hands: dict[str, str]) -> dict[str, str]:
        if set(hands) != set(cls.SEATS):
            raise ValueError("A deal must contain exactly four directional hands.")

        normalized = {}
        for seat in cls.SEATS:
            hand = hands[seat].strip().upper()
            suits = hand.split(".")
            if len(suits) != 4 or any(
                rank not in set(RANKS) | {"-"}
                for suit in suits
                for rank in suit
            ):
                raise ValueError(f"{seat} must use valid four-suit PBN notation.")
            if any("-" in suit and suit != "-" for suit in suits):
                raise ValueError(f"{seat} must use a single dash for a void suit.")
            if any(
                len(suit.replace("-", "")) != len(set(suit.replace("-", "")))
                for suit in suits
            ):
                raise ValueError(f"{seat} has a duplicate card in one or more suits.")
            parsed = PbnParser.parse_hand(hand)
            if sum(len(cards) for cards in parsed.values()) != 13:
                raise ValueError(f"{seat} must contain exactly 13 cards.")
            normalized[seat] = hand

        if not PbnParser.validate_deal(normalized):
            raise ValueError("The deal must contain 52 unique cards with no duplicates.")
        return normalized

    @classmethod
    def _parse_complete_deal(cls, pbn_data: str) -> dict[str, str]:
        seat_aliases = {
            "N": "NORTH",
            "NORTH": "NORTH",
            "E": "EAST",
            "EAST": "EAST",
            "S": "SOUTH",
            "SOUTH": "SOUTH",
            "W": "WEST",
            "WEST": "WEST",
        }
        clockwise_seats = ["NORTH", "EAST", "SOUTH", "WEST"]
        lines = [line.strip() for line in pbn_data.splitlines() if line.strip()]
        hands = {}

        if len(lines) == 1 and ":" in lines[0]:
            starting_seat, deal_text = lines[0].split(":", 1)
            start = seat_aliases.get(starting_seat.strip().upper())
            deal_hands = deal_text.split()
            if start is None or len(deal_hands) != 4:
                raise ValueError("Enter four PBN hands with a valid starting direction.")
            start_index = clockwise_seats.index(start)
            for offset, hand in enumerate(deal_hands):
                seat = clockwise_seats[(start_index + offset) % 4]
                hands[seat] = hand
        else:
            for line in lines:
                if ":" not in line:
                    raise ValueError("Each hand must start with its direction, such as N:.")
                direction, hand = line.split(":", 1)
                seat = seat_aliases.get(direction.strip().upper())
                if seat is None or seat in hands or not hand.strip():
                    raise ValueError("Each direction must have exactly one non-empty hand.")
                hands[seat] = hand.strip()

        return cls._validate_hands(hands)

    def _pbn_hand_counts(self):
        counts = {}
        for seat, hand_input in self.pbn_inputs.items():
            counts[seat] = sum(
                len(cards)
                for cards in PbnParser.parse_hand(hand_input.text()).values()
            )
        return counts

    def _update_pbn_preview(self, seat: str):
        parsed_hand = PbnParser.parse_hand(self.pbn_inputs[seat].text())
        cards = [
            f"{suit}{rank}"
            for suit in self.SUITS
            for rank in parsed_hand[suit]
        ]
        self.pbn_hand_previews[seat].set_hand(cards)

    def _update_validation(self, *_args):
        counts = self._pbn_hand_counts()
        total = sum(counts.values())
        if total < 52:
            self.pbn_validation_label.setText(
                "Cards entered: "
                f"{total}/52. "
                + " | ".join(f"{seat}: {counts[seat]}/13" for seat in self.SEATS)
            )
            pbn_valid = False
        else:
            try:
                self._validate_hands({
                    seat: widget.text()
                    for seat, widget in self.pbn_inputs.items()
                })
                self.pbn_validation_label.setText("Valid deal: all 52 cards are unique.")
                pbn_valid = True
            except ValueError as error:
                self.pbn_validation_label.setText(f"Invalid deal: {error}")
                pbn_valid = False

        self._refresh_picker_buttons()
        self.picker_validation_label.setText(self._picker_status())
        self.btn_save.setEnabled(
            pbn_valid if self.tabs.currentIndex() == 0 else self._picker_is_valid()
        )

    def _refresh_picker_buttons(self, *_args):
        selected_seat = self.selected_seat_combo.currentText()
        counts = {seat: 0 for seat in self.SEATS}
        for code, button in self.card_buttons.items():
            assigned_seat = self.card_assignments.get(code)
            if assigned_seat:
                counts[assigned_seat] += 1
                color = self.SEAT_COLORS[assigned_seat]
                button.setStyleSheet(
                    f"background-color: {color}; color: white; font-weight: bold;"
                )
                button.setToolTip(f"{code}: {assigned_seat} (click to unassign)")
            else:
                suit = code[0]
                text_color = "#b91c1c" if suit in {"H", "D"} else "#111827"
                button.setStyleSheet(
                    f"background-color: #f8fafc; color: {text_color}; "
                    "border: 1px solid #64748b;"
                )
                button.setToolTip(f"{code}: unassigned; click to assign to {selected_seat}")
        counts_are_complete = all(
            count in (0, 13) for count in counts.values()
        )
        has_empty_seat = any(count == 0 for count in counts.values())
        self.btn_randomize.setEnabled(counts_are_complete and has_empty_seat)
        self.picker_counts_label.setText(
            "Assigned cards: "
            + " | ".join(f"{seat}: {counts[seat]}/13" for seat in self.SEATS)
        )
        if hasattr(self, "picker_validation_label"):
            self.picker_validation_label.setText(self._picker_status(counts))
        if hasattr(self, "btn_save"):
            self.btn_save.setEnabled(
                self._picker_is_valid()
                if self.tabs.currentIndex() == 1
                else self._pbn_is_valid()
            )

    def _toggle_card(self, card_code: str):
        selected_seat = self.selected_seat_combo.currentText()
        if self.card_assignments.get(card_code) == selected_seat:
            del self.card_assignments[card_code]
        else:
            self.card_assignments[card_code] = selected_seat
        self._refresh_picker_buttons()

    def _randomize_remaining_cards(self):
        counts = {
            seat: sum(
                assigned_seat == seat
                for assigned_seat in self.card_assignments.values()
            )
            for seat in self.SEATS
        }
        if any(count not in (0, 13) for count in counts.values()):
            return False

        remaining_seats = [
            seat for seat in self.SEATS if counts[seat] == 0
        ]
        if not remaining_seats:
            return False

        assigned_cards = set(self.card_assignments)
        remaining_cards = [
            f"{suit}{rank}"
            for suit in self.SUITS
            for rank in self.RANKS_HIGH_TO_LOW
            if f"{suit}{rank}" not in assigned_cards
        ]
        if len(remaining_cards) != 13 * len(remaining_seats):
            return False

        random.shuffle(remaining_cards)
        for index, seat in enumerate(remaining_seats):
            start = index * 13
            for card_code in remaining_cards[start:start + 13]:
                self.card_assignments[card_code] = seat
        self._refresh_picker_buttons()
        return True

    def _picker_hands(self):
        hands = {seat: {suit: [] for suit in self.SUITS} for seat in self.SEATS}
        for card_code, seat in self.card_assignments.items():
            suit, rank = card_code
            hands[seat][suit].append(rank)
        return {
            seat: ".".join(
                "".join(rank for rank in self.RANKS_HIGH_TO_LOW if rank in hands[seat][suit])
                for suit in self.SUITS
            )
            for seat in self.SEATS
        }

    def _picker_is_valid(self):
        if len(self.card_assignments) != 52:
            return False
        return all(
            sum(assigned_seat == seat for assigned_seat in self.card_assignments.values())
            == 13
            for seat in self.SEATS
        )

    def _picker_status(self, counts=None):
        if counts is None:
            counts = {seat: 0 for seat in self.SEATS}
            for seat in self.card_assignments.values():
                counts[seat] += 1
        if self._picker_is_valid():
            return "Valid deal: all 52 cards are assigned exactly once."
        return "Assign exactly 13 cards to each seat before saving."

    def _pbn_is_valid(self):
        try:
            self._validate_hands({
                seat: widget.text()
                for seat, widget in self.pbn_inputs.items()
            })
            return True
        except ValueError:
            return False

    def _on_tab_changed(self, index: int):
        if index == 1 and self._pbn_is_valid():
            self.card_assignments = {}
            hands = {
                seat: widget.text()
                for seat, widget in self.pbn_inputs.items()
            }
            for seat, hand in hands.items():
                for suit, ranks in PbnParser.parse_hand(hand).items():
                    for rank in ranks:
                        self.card_assignments[f"{suit}{rank}"] = seat
            self._refresh_picker_buttons()
        elif index == 0 and self._picker_is_valid():
            for seat, hand in self._picker_hands().items():
                self.pbn_inputs[seat].setText(hand)
        self.btn_save.setEnabled(
            self._pbn_is_valid() if index == 0 else self._picker_is_valid()
        )

    def save_board(self):
        try:
            if self.tabs.currentIndex() == 0:
                hands = self._validate_hands({
                    seat: widget.text()
                    for seat, widget in self.pbn_inputs.items()
                })
            else:
                if not self._picker_is_valid():
                    raise ValueError("Assign exactly 13 cards to each seat.")
                hands = self._validate_hands(self._picker_hands())
        except ValueError as error:
            show_message(self, "warning", "Invalid deal", str(error))
            return

        try:
            self.saved_board_id = self.repo.save_board(
                case_id=self.case_id,
                hands=hands,
                dealer=self.dealer_combo.currentText(),
                vulnerability=self.vulnerability_combo.currentText(),
                description=self.description_input.text().strip() or None,
                board_id=self.board.id if self.board else None,
            )
        except (sqlite3.Error, LookupError) as error:
            show_message(
                self,
                "critical",
                "Save failed",
                f"Unable to save board: {error}",
            )
            return

        show_message(
            self,
            "information",
            "Saved",
            f"Board #{self.saved_board_id} was saved successfully.",
        )
        self.accept()
