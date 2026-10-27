import json
import sqlite3
from typing import Optional

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from src.core.bridge_logic import BridgeLogic
from src.database.repository import Repository
from src.ui.i18n import show_message


class ScenarioEditorDialog(QDialog):
    """Create or edit the contract and playback details of a scenario."""

    def __init__(
        self,
        board_id: int,
        scenario=None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Scenario Editor")
        self.resize(620, 480)
        self.board_id = board_id
        self.scenario = scenario
        self.repo = Repository()
        self.saved_scenario_id: Optional[int] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.bidding_route_input = QLineEdit(
            self.scenario.bidding_route if self.scenario else ""
        )
        self.bidding_route_input.setPlaceholderText("1H PASS 4H PASS PASS PASS")
        form.addRow("Bidding route:", self.bidding_route_input)

        self.contract_input = QLineEdit(
            self.scenario.contract if self.scenario else ""
        )
        self.contract_input.setPlaceholderText("4H or PASSED_OUT")
        form.addRow("Contract:", self.contract_input)

        self.declarer_combo = QComboBox()
        self.declarer_combo.addItems(["SOUTH", "WEST", "NORTH", "EAST"])
        if self.scenario:
            self.declarer_combo.setCurrentText(self.scenario.declarer)
        form.addRow("Declarer:", self.declarer_combo)

        self.risk_combo = QComboBox()
        self.risk_combo.addItems(["NONE", "DOUBLE", "REDOUBLE"])
        if self.scenario:
            self.risk_combo.setCurrentText(self.scenario.risk_status)
        form.addRow("Risk status:", self.risk_combo)

        self.targeted_checkbox = QCheckBox("Enable target-sequence playback")
        self.targeted_checkbox.setChecked(
            bool(self.scenario and self.scenario.is_targeted)
        )
        form.addRow("", self.targeted_checkbox)

        self.target_sequence_input = QLineEdit(
            self.scenario.targeted_sequence
            if self.scenario and self.scenario.targeted_sequence
            else ""
        )
        self.target_sequence_input.setPlaceholderText('["SA", "HK", "D7"]')
        form.addRow("Target sequence (JSON):", self.target_sequence_input)
        self.information_input = QPlainTextEdit(
            self.scenario.information if self.scenario else ""
        )
        self.information_input.setPlaceholderText(
            "Optional plain-text information for this scenario"
        )
        self.information_input.setMaximumHeight(110)
        form.addRow("Information:", self.information_input)
        layout.addLayout(form)
        layout.addWidget(
            QLabel("Enter card codes in suit-rank order, for example SA or HT.")
        )

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.btn_save = QPushButton("Save")
        self.btn_save.clicked.connect(self.save_scenario)
        buttons.addWidget(self.btn_save)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        buttons.addWidget(self.btn_cancel)
        layout.addLayout(buttons)

    def _validated_target_sequence(self):
        value = self.target_sequence_input.text().strip()
        if not value:
            if self.targeted_checkbox.isChecked():
                raise ValueError("A target sequence is required in target mode.")
            return json.dumps([])

        sequence = json.loads(value)
        if not isinstance(sequence, list) or any(
            not isinstance(card, str)
            or len(card.strip()) != 2
            or card.strip()[0].upper() not in "SHDC"
            or card.strip()[1].upper() not in "23456789TJQKA"
            for card in sequence
        ):
            raise ValueError(
                'Enter a JSON list of suit-rank card codes, such as ["SA", "HK"].'
            )
        normalized = [card.strip().upper() for card in sequence]
        if self.targeted_checkbox.isChecked() and not normalized:
            raise ValueError("A target sequence cannot be empty.")
        if len(normalized) != len(set(normalized)):
            raise ValueError("A target sequence cannot play the same card twice.")
        return json.dumps(normalized)

    def save_scenario(self):
        bidding_route = self.bidding_route_input.text().strip()
        contract = self.contract_input.text().strip().upper()
        declarer = self.declarer_combo.currentText()
        risk_status = self.risk_combo.currentText()
        is_targeted = int(self.targeted_checkbox.isChecked())

        if contract and contract != "PASSED_OUT":
            parsed_contract = BridgeLogic.parse_call(contract)
            if not parsed_contract or parsed_contract.get("type") != "BID":
                show_message(
                    self,
                    "warning",
                    "Invalid contract",
                    "Enter a valid bridge contract such as 3NT, or PASSED_OUT.",
                )
                return

        try:
            target_sequence = self._validated_target_sequence()
        except (ValueError, json.JSONDecodeError) as error:
            show_message(
                self,
                "warning",
                "Invalid target sequence",
                str(error),
            )
            return

        try:
            if self.scenario:
                self.repo.update_scenario(
                    self.scenario.id,
                    bidding_route,
                    declarer,
                    contract,
                    risk_status,
                    is_targeted,
                    target_sequence,
                    self.information_input.toPlainText(),
                )
                self.saved_scenario_id = self.scenario.id
            else:
                self.saved_scenario_id = self.repo.create_scenario(
                    self.board_id,
                    bidding_route,
                    declarer,
                    contract,
                    risk_status,
                    is_targeted,
                    target_sequence,
                    information=self.information_input.toPlainText(),
                )
        except sqlite3.Error as error:
            show_message(
                self,
                "critical",
                "Save failed",
                f"Unable to save scenario: {error}",
            )
            return

        self.accept()
