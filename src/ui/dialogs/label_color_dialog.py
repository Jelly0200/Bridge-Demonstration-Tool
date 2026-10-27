from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QWidget,
)


class LabelColorDialog(QDialog):
    """Choose a behavioral label color for a card."""

    COLORS = ("RED", "ORANGE", "YELLOW", "BLUE", "PURPLE", "GREEN")
    COLOR_STYLES = {
        "RED": ("#e74c3c", "#ffffff"),
        "ORANGE": ("#f97316", "#ffffff"),
        "YELLOW": ("#f1c40f", "#1f2937"),
        "BLUE": ("#3498db", "#ffffff"),
        "PURPLE": ("#a855f7", "#ffffff"),
        "GREEN": ("#2ecc71", "#1f2937"),
    }

    def __init__(
        self,
        card_code: str,
        current_color="RED",
        parent=None,
        current_sequence=1,
        sequence_counts=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(f"Label {card_code}")
        self.selected_color = current_color
        self.selected_sequence = current_sequence
        self.sequence_counts = sequence_counts or {}
        layout = QFormLayout(self)
        color_bar = QWidget(self)
        self.color_bar = color_bar
        color_layout = QHBoxLayout(color_bar)
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_layout.setSpacing(6)
        self.color_group = QButtonGroup(self)
        self.color_group.setExclusive(True)
        self.color_buttons = {}
        for color in self.COLORS:
            button = QPushButton(color, color_bar)
            button.setCheckable(True)
            button.setMinimumSize(76, 40)
            background, foreground = self.COLOR_STYLES[color]
            button.setStyleSheet(
                f"QPushButton {{ background-color: {background}; "
                f"color: {foreground}; font-weight: bold; border: 2px solid "
                f"transparent; border-radius: 5px; }}"
                "QPushButton:checked { border: 4px inset #0b1120; }"
            )
            button.setProperty("labelColor", color)
            button.clicked.connect(self._select_color)
            self.color_group.addButton(button)
            color_layout.addWidget(button)
            self.color_buttons[color] = button
        if current_color in self.color_buttons:
            self.color_buttons[current_color].setChecked(True)
        layout.addRow(QLabel(f"Label color for {card_code}:", self))
        layout.addRow(color_bar)
        self.btn_clear = QPushButton("Clear label")
        self.btn_clear.clicked.connect(self._clear_color)
        layout.addRow("", self.btn_clear)
        self.sequence_spin = QSpinBox()
        self.sequence_spin.setRange(1, 999)
        self.sequence_spin.setValue(current_sequence)
        layout.addRow("Label sequence:", self.sequence_spin)
        buttons = QHBoxLayout()
        self.btn_apply = QPushButton("Apply")
        self.btn_apply.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(self.btn_apply)
        buttons.addWidget(self.btn_cancel)
        layout.addRow(buttons)
        self.setMinimumSize(800, 230)
        self.resize(800, 230)

    def accept(self):
        self.selected_sequence = self.sequence_spin.value()
        super().accept()

    def _select_color(self):
        button = self.sender()
        self.selected_color = button.property("labelColor")
        sequence = self.sequence_counts.get(self.selected_color)
        if sequence is not None:
            self.sequence_spin.setValue(sequence)

    def _clear_color(self):
        self.color_group.setExclusive(False)
        for button in self.color_buttons.values():
            button.setChecked(False)
        self.color_group.setExclusive(True)
        self.selected_color = "NONE"
