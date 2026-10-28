from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QFontMetrics


class CardWidget(QFrame):
    """Card widget showing its face, label highlight, and DDS trick estimate."""
    card_clicked = pyqtSignal(str)
    card_context_requested = pyqtSignal(str)

    COLOR_MAP = {
        'RED': '#e74c3c',
        'ORANGE': '#f97316',
        'YELLOW': '#f1c40f',
        'BLUE': '#3498db',
        'PURPLE': '#a855f7',
        'GREEN': '#2ecc71',
        'NONE': 'transparent'
    }

    SUIT_SYMBOLS = {'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣'}
    SUIT_COLORS = {'S': '#1a1a1a', 'H': '#d63031', 'D': '#d63031', 'C': '#1a1a1a'}

    def __init__(
        self,
        card_code: str,
        parent=None,
        compact: bool = False,
        large: bool = False,
    ):
        super().__init__(parent)
        self.card_code = card_code
        self.suit = card_code[0] if card_code else 'S'
        self.rank = card_code[1:] if len(card_code) > 1 else card_code
        self.compact = compact
        self.large = large

        self.label_color = 'NONE'
        self.label_sequence = None
        self.dds_tricks = None
        self.is_hidden = False

        self.init_ui()

    def init_ui(self):
        if self.large:
            self.setFixedSize(52, 72)
        elif self.compact:
            self.setFixedSize(24, 34)
        else:
            self.setFixedSize(44, 62)
        self.setFrameShape(QFrame.Shape.StyledPanel)

        symbol = self.SUIT_SYMBOLS.get(self.suit, '')
        text_color = self.SUIT_COLORS.get(self.suit, '#000000')
        rank_font_size = 7 if self.compact else 16 if self.large else 14
        suit_font_size = 12 if self.compact else 32 if self.large else 30
        sequence_font_size = 7 if self.compact else 10 if self.large else 10
        dds_font_size = 6 if self.compact else 7
        rank_height = 8 if self.compact else 18 if self.large else 16
        dds_height = 7 if self.compact else 9
        dds_width = 16 if self.compact else 22

        layout = QGridLayout(self)
        layout.setContentsMargins(2, 1, 2, 1)
        layout.setHorizontalSpacing(0)
        layout.setVerticalSpacing(0)

        self.rank_label = QLabel(self.rank, self)
        self.rank_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self.rank_label.setFont(QFont("Arial", rank_font_size, QFont.Weight.Bold))
        self.rank_label.setFixedHeight(rank_height)
        self.rank_label.setStyleSheet(
            f"color: {text_color}; background: transparent;"
        )

        self.sequence_label = QLabel("", self)
        self.sequence_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop
        )
        self.sequence_label.setFont(
            QFont("Arial", sequence_font_size, QFont.Weight.Bold)
        )
        sequence_height = max(
            dds_height,
            QFontMetrics(self.sequence_label.font()).height() + 2,
        )
        self.sequence_label.setFixedHeight(sequence_height)
        self.sequence_label.hide()

        self.card_label = QLabel(symbol, self)
        self.card_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.card_label.setFont(QFont("Arial", suit_font_size, QFont.Weight.Bold))
        self.card_label.setStyleSheet(
            f"color: {text_color}; background: transparent;"
        )

        self.dds_label = QLabel("", self)
        self.dds_label.setObjectName("dds_card_value")
        self.dds_label.setProperty("bilingualExempt", True)
        self.dds_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dds_label.setFont(QFont("Arial", dds_font_size, QFont.Weight.Bold))
        self.dds_label.setFixedSize(dds_width, dds_height)
        self.dds_label.setStyleSheet(
            "color: #075985; background-color: #e0f2fe; border-radius: 2px;"
        )
        self.dds_label.hide()
        for label in (
            self.rank_label,
            self.sequence_label,
            self.card_label,
            self.dds_label,
        ):
            label.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                True,
            )

        layout.addWidget(
            self.rank_label,
            0,
            0,
            alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
        )
        layout.addWidget(
            self.sequence_label,
            0,
            1,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
        )
        layout.addWidget(self.card_label, 1, 0, 1, 2)
        layout.addWidget(
            self.dds_label,
            2,
            0,
            1,
            2,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
        )
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setRowStretch(1, 1)

        self.update_style()

    def set_card_code(self, card_code: str):
        self.card_code = card_code
        self.suit = card_code[0] if card_code else "S"
        self.rank = card_code[1:] if len(card_code) > 1 else card_code
        self.label_color = "NONE"
        self.label_sequence = None
        self.dds_tricks = None
        self.is_hidden = False

        symbol = self.SUIT_SYMBOLS.get(self.suit, "")
        text_color = self.SUIT_COLORS.get(self.suit, "#000000")
        self.rank_label.setText(self.rank)
        self.rank_label.setStyleSheet(
            f"color: {text_color}; background: transparent;"
        )
        self.rank_label.show()
        self.sequence_label.clear()
        self.sequence_label.hide()
        self.card_label.setText(symbol)
        self.card_label.setStyleSheet(
            f"color: {text_color}; background: transparent;"
        )
        self.card_label.show()
        self.dds_label.clear()
        self.dds_label.hide()
        self.update_style()

    def set_hidden(self, hidden: bool):
        self.is_hidden = hidden
        if hidden:
            self.rank_label.hide()
            self.sequence_label.hide()
            self.card_label.setText("")
            self.dds_label.setText("")
            self.dds_label.hide()
        else:
            self.rank_label.setText(self.rank)
            self.rank_label.show()
            if self.label_sequence is not None and self.label_color != "NONE":
                self.sequence_label.show()
            symbol = self.SUIT_SYMBOLS.get(self.suit, '')
            self.card_label.setText(symbol)
            text_color = self.SUIT_COLORS.get(self.suit, '#000000')
            self.card_label.setStyleSheet(f"color: {text_color}; background: transparent;")
            if self.dds_tricks is not None:
                self.dds_label.setText(str(self.dds_tricks))
                self.dds_label.show()
            else:
                self.dds_label.hide()
        self.update_style()

    def set_label_color(self, color_name: str):
        self.label_color = color_name.upper()
        if self.label_color == "NONE":
            self.set_label_sequence(None)
        elif self.label_sequence is not None:
            self._update_sequence_style()
        self.update_style()

    def set_label_sequence(self, sequence: int | None):
        self.label_sequence = sequence
        self.sequence_label.setText(
            str(sequence) if sequence is not None else ""
        )
        if sequence is None or self.label_color == "NONE" or self.is_hidden:
            self.sequence_label.hide()
            return
        self._update_sequence_style()
        self.sequence_label.show()

    def _update_sequence_style(self):
        sequence_color = self.COLOR_MAP.get(self.label_color, "#e2e8f0")
        self.sequence_label.setStyleSheet(
            f"color: {sequence_color}; background: transparent;"
        )

    def set_dds_tricks(self, tricks: int | None):
        self.dds_tricks = tricks
        if tricks is not None and not self.is_hidden:
            self.dds_label.setText(str(tricks))
            self.dds_label.show()
        else:
            self.dds_label.setText("")
            self.dds_label.hide()

    def update_style(self):
        if self.is_hidden:
            border_color = "#bdc3c7"
            border_width = "1px"
            bg_color = "#34495e"
        else:
            border_color = self.COLOR_MAP.get(self.label_color, "#bdc3c7")
            border_width = "3px" if self.label_color != "NONE" else "1px"
            bg_color = "#ffffff"
        self.setStyleSheet(f"""
            CardWidget {{
                background-color: {bg_color};
                border: {border_width} solid {border_color};
                border-radius: 5px;
            }}
            CardWidget:hover {{
                border-color: #e67e22;
            }}
        """)

    def mousePressEvent(self, event):
        is_context_click = (
            event.button() == Qt.MouseButton.RightButton
            or (
                event.button() == Qt.MouseButton.LeftButton
                and event.modifiers() & Qt.KeyboardModifier.ControlModifier
            )
        )
        if is_context_click:
            self.card_context_requested.emit(self.card_code)
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton:
            self.card_clicked.emit(self.card_code)
            event.accept()
        else:
            super().mousePressEvent(event)


class HandWidget(QWidget):
    card_selected = pyqtSignal(str)
    card_context_requested = pyqtSignal(str, str)

    def __init__(self, position: str = "SOUTH", parent=None):
        super().__init__(parent)
        self.position = position
        self.cards = []
        self.horizontal = position in ["NORTH", "SOUTH"]
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(1, 1, 1, 1)
        self.main_layout.setSpacing(2)

    def set_horizontal(self, horizontal: bool):
        if self.horizontal == horizontal:
            return
        card_codes = [card.card_code for card in self.cards]
        self.horizontal = horizontal
        self.set_hand(card_codes, force_rebuild=True)

    def set_hand(self, card_codes: list[str], force_rebuild: bool = False):
        if (
            not force_rebuild
            and card_codes == [card.card_code for card in self.cards]
        ):
            return

        existing_cards = {card.card_code: card for card in self.cards}
        self._clear_layout(self.main_layout, preserve_widgets=True)
        self.cards.clear()

        if self.horizontal:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(2)
            for code in card_codes:
                row.addWidget(self._reuse_or_make_card(code, existing_cards))
            row.addStretch(1)
            self.main_layout.addLayout(row)
        else:
            cards_by_suit = {suit: [] for suit in "SHDC"}
            for code in card_codes:
                cards_by_suit.setdefault(code[0], []).append(code)
            suit_symbols = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}
            for suit in "SHDC":
                row = QHBoxLayout()
                row.setContentsMargins(0, 0, 0, 0)
                row.setSpacing(1)
                suit_label = QLabel(suit_symbols[suit])
                suit_label.setFixedWidth(16)
                suit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                suit_color = "#fca5a5" if suit in {"H", "D"} else "#e2e8f0"
                suit_label.setStyleSheet(
                    f"color: {suit_color}; font-weight: bold;"
                )
                row.addWidget(suit_label)
                for code in cards_by_suit[suit]:
                    row.addWidget(self._reuse_or_make_card(code, existing_cards))
                row.addStretch(1)
                self.main_layout.addLayout(row)

        for card_widget in existing_cards.values():
            card_widget.deleteLater()

    def _reuse_or_make_card(
        self,
        code: str,
        existing_cards: dict[str, CardWidget],
    ) -> CardWidget:
        card_widget = existing_cards.pop(code, None)
        if card_widget is None:
            return self._make_card(code, compact=False)
        card_widget.show()
        self.cards.append(card_widget)
        return card_widget

    def _make_card(self, code: str, compact: bool) -> CardWidget:
        card_widget = CardWidget(code, self, compact=compact)
        card_widget.card_clicked.connect(self.card_selected.emit)
        card_widget.card_context_requested.connect(
            lambda card, position=self.position: self.card_context_requested.emit(
                position,
                card,
            )
        )
        self.cards.append(card_widget)
        return card_widget

    @classmethod
    def _clear_layout(cls, layout, preserve_widgets: bool = False):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                if preserve_widgets and isinstance(item.widget(), CardWidget):
                    item.widget().hide()
                else:
                    item.widget().deleteLater()
            elif item.layout():
                cls._clear_layout(item.layout(), preserve_widgets)
                item.layout().deleteLater()

    def set_hidden(self, hidden: bool):
        for card in self.cards:
            card.set_hidden(hidden)
            card.setVisible(not hidden)