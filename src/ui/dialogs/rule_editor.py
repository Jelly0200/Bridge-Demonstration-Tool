import json

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from src.ui.i18n import show_message


class RuleEditorDialog(QDialog):
    """Edit a scenario's optional target sequence and card labels."""

    LABEL_COLORS = {"RED", "ORANGE", "YELLOW", "BLUE", "PURPLE", "GREEN"}
    VALID_SUITS = set("SHDC")
    VALID_RANKS = set("23456789TJQKA")

    def __init__(self, scenario, labels=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scenario rules")
        self.resize(620, 520)
        self.scenario = scenario
        self.saved_labels = []
        self.saved_risk_status = scenario.risk_status
        self.saved_is_targeted = int(bool(scenario.is_targeted))
        self.saved_targeted_sequence = scenario.targeted_sequence or "[]"
        self._init_ui(labels or [])

    def _init_ui(self, labels):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Risk status:"))
        self.risk_combo = QComboBox()
        self.risk_combo.addItems(["NONE", "DOUBLE", "REDOUBLE"])
        self.risk_combo.setCurrentText(self.scenario.risk_status)
        layout.addWidget(self.risk_combo)

        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("Targeted playback:"))
        self.target_combo = QComboBox()
        self.target_combo.addItems(["Disabled", "Enabled"])
        self.target_combo.setCurrentIndex(int(bool(self.scenario.is_targeted)))
        target_layout.addWidget(self.target_combo)
        target_layout.addStretch()
        layout.addLayout(target_layout)

        layout.addWidget(QLabel("Target card sequence (JSON):"))
        self.seq_input = QLineEdit(self.scenario.targeted_sequence or "")
        self.seq_input.setPlaceholderText('["SA", "SK", "HQ"]')
        layout.addWidget(self.seq_input)

        layout.addWidget(QLabel("Card labels:"))
        self.label_table = QTableWidget(0, 3)
        self.label_table.setHorizontalHeaderLabels(["Sequence", "Color", "Card"])
        self.label_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.label_table)
        self._set_labels(labels)

        label_actions = QHBoxLayout()
        self.btn_add_label = QPushButton("Add label")
        self.btn_add_label.clicked.connect(self._add_label_row)
        label_actions.addWidget(self.btn_add_label)
        self.btn_remove_label = QPushButton("Remove selected")
        self.btn_remove_label.clicked.connect(self._remove_selected_labels)
        label_actions.addWidget(self.btn_remove_label)
        label_actions.addStretch()
        layout.addLayout(label_actions)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.btn_save = QPushButton("Apply")
        self.btn_save.clicked.connect(self.save_rules)
        buttons.addWidget(self.btn_save)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        buttons.addWidget(self.btn_cancel)
        layout.addLayout(buttons)

    def _set_labels(self, labels):
        self.label_table.setRowCount(len(labels))
        for row, label in enumerate(labels):
            values = (
                label.sequence if hasattr(label, "sequence") else label["Sequence"],
                label.color if hasattr(label, "color") else label["Color"],
                label.card if hasattr(label, "card") else label["Card"],
            )
            for column, value in enumerate(values):
                self.label_table.setItem(
                    row,
                    column,
                    QTableWidgetItem(str(value)),
                )

    def _add_label_row(self):
        row = self.label_table.rowCount()
        self.label_table.insertRow(row)
        self.label_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.label_table.setItem(row, 1, QTableWidgetItem("RED"))
        self.label_table.setItem(row, 2, QTableWidgetItem(""))
        self.label_table.setCurrentCell(row, 2)

    def _remove_selected_labels(self):
        for row in sorted(
            {index.row() for index in self.label_table.selectedIndexes()},
            reverse=True,
        ):
            self.label_table.removeRow(row)

    def _validated_target_sequence(self):
        raw_sequence = self.seq_input.text().strip()
        if not raw_sequence:
            sequence = []
        else:
            sequence = json.loads(raw_sequence)
        if not isinstance(sequence, list):
            raise ValueError("The target sequence must be a JSON list.")

        normalized = []
        for card in sequence:
            if not isinstance(card, str):
                raise ValueError("Each target card must be a suit-rank code.")
            card_code = card.strip().upper()
            if (
                len(card_code) != 2
                or card_code[0] not in self.VALID_SUITS
                or card_code[1] not in self.VALID_RANKS
            ):
                raise ValueError(f"Invalid target card: {card}")
            normalized.append(card_code)

        if len(normalized) != len(set(normalized)):
            raise ValueError("A target sequence cannot repeat a card.")
        if self.target_combo.currentIndex() == 1 and not normalized:
            raise ValueError("Add at least one card to enable targeted playback.")
        return normalized

    def _validated_labels(self):
        labels = []
        for row in range(self.label_table.rowCount()):
            values = [
                self.label_table.item(row, column).text().strip()
                if self.label_table.item(row, column)
                else ""
                for column in range(3)
            ]
            if not any(values):
                continue
            if not all(values):
                raise ValueError(f"Complete all fields in label row {row + 1}.")

            try:
                sequence = int(values[0])
            except ValueError as error:
                raise ValueError(
                    f"Label row {row + 1} needs a positive sequence number."
                ) from error
            color = values[1].upper()
            card = values[2].upper()
            if sequence < 1:
                raise ValueError("Label sequence numbers must be positive.")
            if color not in self.LABEL_COLORS:
                raise ValueError(f"Invalid label color in row {row + 1}.")
            if (
                len(card) != 2
                or card[0] not in self.VALID_SUITS
                or card[1] not in self.VALID_RANKS
            ):
                raise ValueError(f"Invalid card code in label row {row + 1}.")
            labels.append(
                {"Sequence": sequence, "Color": color, "Card": card}
            )
        return labels

    def save_rules(self):
        try:
            target_sequence = self._validated_target_sequence()
            labels = self._validated_labels()
        except (ValueError, json.JSONDecodeError) as error:
            show_message(
                self,
                "warning",
                "Invalid scenario rules",
                str(error),
            )
            return

        self.saved_risk_status = self.risk_combo.currentText()
        self.saved_is_targeted = self.target_combo.currentIndex()
        self.saved_targeted_sequence = json.dumps(target_sequence)
        self.saved_labels = labels
        self.accept()
