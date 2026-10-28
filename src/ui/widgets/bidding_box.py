from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from config.constants import PLAYER_NEXT
from src.core.bridge_logic import BridgeLogic


class BiddingBoxDialog(QDialog):
    """Edit an auction in a seat-aligned grid and choose its risk status."""

    bid_made = pyqtSignal(str)

    STRAINS = (("♣", "C"), ("♦", "D"), ("♥", "H"), ("♠", "S"), ("NT", "NT"))

    def __init__(
        self,
        current_bidding_history=None,
        dealer="NORTH",
        risk_status="NONE",
        information=None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Scenario Settings")
        self.resize(780, 800)
        self.setMinimumSize(720, 700)
        self.bidding_history = list(current_bidding_history or [])
        self.dealer = dealer.upper()
        self.risk_status = risk_status
        self.information = information or ""
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        self.auction_table = QTableWidget(0, 4)
        self.auction_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.auction_table.setSelectionMode(
            QTableWidget.SelectionMode.NoSelection
        )
        self.auction_table.setMinimumHeight(230)
        self.auction_table.setStyleSheet(
            "QTableWidget::item { padding: 7px; font-size: 15px; }"
        )
        self.auction_table.verticalHeader().hide()
        layout.addWidget(QLabel("Auction"))
        layout.addWidget(self.auction_table)

        call_layout = QGridLayout()
        call_layout.setHorizontalSpacing(8)
        call_layout.setVerticalSpacing(5)
        call_layout.addWidget(QLabel("Level"), 0, 0)
        for column, (suit_symbol, _strain) in enumerate(self.STRAINS, start=1):
            suit_label = QLabel(suit_symbol)
            suit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            suit_label.setStyleSheet("font-size: 19px; font-weight: bold;")
            call_layout.addWidget(suit_label, 0, column)

        self.call_buttons = {}
        for row, level in enumerate("1234567", start=1):
            call_layout.addWidget(QLabel(level), row, 0)
            for column, (_symbol, strain) in enumerate(self.STRAINS, start=1):
                call = f"{level}{strain}"
                button = QPushButton(call)
                button.setFixedSize(70, 36)
                button.setStyleSheet(
                    "padding: 2px 5px; font-size: 13px; font-weight: bold;"
                )
                button.clicked.connect(
                    lambda _checked=False, value=call: self.add_call(value)
                )
                self.call_buttons[call] = button
                call_layout.addWidget(button, row, column)
        layout.addLayout(call_layout)

        special_calls = QHBoxLayout()
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
        layout.addLayout(special_calls)

        risk_layout = QHBoxLayout()
        risk_layout.addWidget(QLabel("Risk status:"))
        self.risk_combo = QComboBox()
        self.risk_combo.addItems(["NONE", "DOUBLE", "REDOUBLE"])
        self.risk_combo.setCurrentText(self.risk_status)
        risk_layout.addWidget(self.risk_combo)
        risk_layout.addStretch()
        layout.addLayout(risk_layout)

        layout.addWidget(QLabel("Information"))
        self.information_editor = QPlainTextEdit(self.information)
        self.information_editor.setPlaceholderText(
            "Optional plain-text information for this scenario"
        )
        self.information_editor.setMaximumHeight(110)
        layout.addWidget(self.information_editor)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.btn_save = QPushButton("Apply")
        self.btn_save.clicked.connect(self._apply)
        buttons.addWidget(self.btn_save)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        buttons.addWidget(self.btn_cancel)
        layout.addLayout(buttons)
        self._refresh_auction()

    def _apply(self):
        self.information = self.information_editor.toPlainText()
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
        for index, call in enumerate(self.bidding_history):
            row, column = divmod(index, 4)
            item = QTableWidgetItem(call)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.auction_table.setItem(row, column, item)
        self.auction_table.resizeColumnsToContents()
        self.auction_table.resizeRowsToContents()

        complete = self._auction_complete()
        for call, button in self.call_buttons.items():
            button.setEnabled(
                not complete
                and BridgeLogic.is_legal_call(call, self.bidding_history)
            )
        for call, button in self.special_buttons.items():
            button.setEnabled(
                not complete
                and BridgeLogic.is_legal_call(call, self.bidding_history)
            )
        self.btn_undo.setEnabled(bool(self.bidding_history))

    def add_call(self, call: str):
        if self._auction_complete() or not BridgeLogic.is_legal_call(
            call,
            self.bidding_history,
        ):
            return
        self.bidding_history.append(call)
        self.bid_made.emit(call)
        self._refresh_auction()

    def undo_call(self):
        if self.bidding_history:
            self.bidding_history.pop()
            self._refresh_auction()
