from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config.constants import PLAYER_NEXT
from src.core.bridge_logic import BridgeLogic


class BiddingBoxDialog(QDialog):
    """Edit an auction and show its derived doubling status."""

    bid_made = pyqtSignal(str)

    STRAINS = (("NT", "NT"), ("♠", "S"), ("♥", "H"), ("♦", "D"), ("♣", "C"))
    STRAIN_COLORS = {
        "NT": "#9ca3af",
        "S": "#3b82f6",
        "H": "#f87171",
        "D": "#fbbf24",
        "C": "#4ade80",
    }

    def __init__(
        self,
        current_bidding_history=None,
        dealer="NORTH",
        parent=None,
        read_only=False,
        route_only=False,
    ):
        super().__init__(parent)
        self.setWindowTitle("Bidding")
        self.bidding_history = list(current_bidding_history or [])
        self.dealer = dealer.upper()
        self.read_only = read_only
        self.route_only = route_only
        self.risk_status = BridgeLogic.derive_risk_status(self.bidding_history)
        self._init_ui()
        self.adjustSize()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        self.auction_table = QTableWidget(0, 4)
        self.auction_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.auction_table.setSelectionMode(
            QTableWidget.SelectionMode.NoSelection
        )
        self.auction_table.setFixedWidth(560)
        self.auction_table.setMinimumHeight(0)
        self.auction_table.setStyleSheet(
            "QTableWidget::item { padding: 7px; }"
        )
        self.auction_table.verticalHeader().hide()
        self.auction_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.auction_label = QLabel(
            "Bidding route" if self.route_only else "Auction"
        )
        self.auction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(
            self.auction_label,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )
        layout.addWidget(
            self.auction_table,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )

        call_layout = QGridLayout()
        call_layout.setContentsMargins(0, 0, 0, 0)
        call_layout.setHorizontalSpacing(5)
        call_layout.setVerticalSpacing(4)
        level_header = QLabel("Level")
        level_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        call_layout.addWidget(level_header, 0, 0)
        for column, (suit_symbol, strain) in enumerate(self.STRAINS, start=1):
            suit_label = QLabel(suit_symbol)
            suit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            suit_label.setStyleSheet(
                f"font-weight: bold; color: {self.STRAIN_COLORS[strain]};"
            )
            call_layout.addWidget(suit_label, 0, column)

        self.call_buttons = {}
        for row, level in enumerate("1234567", start=1):
            level_label = QLabel(level)
            level_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            call_layout.addWidget(level_label, row, 0)
            for column, (_symbol, strain) in enumerate(self.STRAINS, start=1):
                call = f"{level}{strain}"
                button = QPushButton(call)
                button.setFixedSize(76, 36)
                button.setStyleSheet(
                    "padding: 2px 5px; font-weight: bold; "
                    f"color: {self.STRAIN_COLORS[strain]};"
                )
                button.clicked.connect(
                    lambda _checked=False, value=call: self.add_call(value)
                )
                self.call_buttons[call] = button
                call_layout.addWidget(button, row, column)
        self.call_matrix = QWidget(self)
        self.call_matrix.setLayout(call_layout)
        self.call_matrix.setVisible(not self.route_only)
        layout.addWidget(
            self.call_matrix,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )

        self.special_controls = QWidget(self)
        special_calls = QHBoxLayout(self.special_controls)
        special_calls.setContentsMargins(0, 0, 0, 0)
        self.special_buttons = {}
        for call, caption in (
            ("PASS", "Pass"),
            ("DBL", "Double"),
            ("RDBL", "Redouble"),
        ):
            button = QPushButton(caption)
            button.clicked.connect(
                lambda _checked=False, value=call: self.add_call(value)
            )
            self.special_buttons[call] = button
            special_calls.addWidget(button)
        self.btn_undo = QPushButton("Undo last call")
        self.btn_undo.clicked.connect(self.undo_call)
        special_calls.addWidget(self.btn_undo)
        self.special_controls.setVisible(not self.route_only)
        layout.addWidget(self.special_controls)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.btn_save = QPushButton("Apply")
        self.btn_save.clicked.connect(self._apply)
        self.btn_save.setVisible(not self.read_only)
        buttons.addWidget(self.btn_save)
        self.btn_cancel = QPushButton("Close" if self.read_only else "Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        buttons.addWidget(self.btn_cancel)
        layout.addLayout(buttons)
        self._refresh_auction()

    def _apply(self):
        if self.read_only:
            return
        self.accept()

    def _auction_complete(self):
        history = self.bidding_history
        return (
            len(history) == 4 and all(call in {"PASS", "P"} for call in history)
        ) or (
            len(history) >= 4
            and all(call in {"PASS", "P"} for call in history[-3:])
        )

    def _refresh_auction(self):
        seat_order = [self.dealer]
        for _ in range(3):
            seat_order.append(PLAYER_NEXT[seat_order[-1]])
        self.auction_table.clearContents()
        self.auction_table.setColumnCount(4)
        self.auction_table.setHorizontalHeaderLabels(seat_order)
        rows = (len(self.bidding_history) + 3) // 4
        self.auction_table.setRowCount(rows)
        for row in range(rows):
            self.auction_table.setRowHeight(row, 32)
        for index, call in enumerate(self.bidding_history):
            row, column = divmod(index, 4)
            item = QTableWidgetItem(call)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            color = self._call_color(call)
            if color:
                item.setForeground(QColor(color))
            self.auction_table.setItem(row, column, item)
        self.auction_table.setFixedHeight(
            self.auction_table.horizontalHeader().height()
            + rows * 32
            + 2
        )
        self.risk_status = BridgeLogic.derive_risk_status(
            self.bidding_history
        )

        complete = self._auction_complete()
        for call, button in self.call_buttons.items():
            button.setEnabled(
                not self.read_only
                and not complete
                and BridgeLogic.is_legal_call(call, self.bidding_history)
            )
        for call, button in self.special_buttons.items():
            button.setEnabled(
                not self.read_only
                and not complete
                and BridgeLogic.is_legal_call(call, self.bidding_history)
            )
        self.btn_undo.setEnabled(
            not self.read_only and bool(self.bidding_history)
        )

    @classmethod
    def _call_color(cls, call: str) -> str | None:
        normalized = call.strip().upper()
        if not normalized or normalized[0] not in "1234567":
            return None
        strain = "NT" if normalized.endswith("NT") else normalized[-1]
        return cls.STRAIN_COLORS.get(strain)

    def add_call(self, call: str):
        if (
            self.read_only
            or self._auction_complete()
            or not BridgeLogic.is_legal_call(call, self.bidding_history)
        ):
            return
        self.bidding_history.append(call)
        self.bid_made.emit(call)
        self._refresh_auction()

    def undo_call(self):
        if not self.read_only and self.bidding_history:
            self.bidding_history.pop()
            self._refresh_auction()
