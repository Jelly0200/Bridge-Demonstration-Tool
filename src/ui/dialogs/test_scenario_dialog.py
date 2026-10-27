from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from src.ui.i18n import translate_text


class TestScenarioDialog(QDialog):
    def __init__(
        self,
        title: str,
        heading: str,
        *,
        details: tuple[tuple[str, str], ...] = (),
        information: str = "",
        action_text: str = "Continue",
        language: str = "en",
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(translate_text(title, language))
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 22)
        layout.setSpacing(16)

        eyebrow = QLabel(translate_text("TEST SESSION", language))
        eyebrow.setObjectName("eyebrow")
        layout.addWidget(eyebrow)

        title_label = QLabel(translate_text(heading, language))
        title_label.setObjectName("dialogHeading")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        if details:
            details_layout = QGridLayout()
            details_layout.setSpacing(10)
            for index, (label, value) in enumerate(details):
                card = QFrame(self)
                card.setObjectName("metricCard")
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(14, 11, 14, 11)
                card_layout.setSpacing(5)

                label_widget = QLabel(translate_text(label, language), card)
                label_widget.setObjectName("metricLabel")
                value_widget = QLabel(str(value), card)
                value_widget.setObjectName("metricValue")
                value_widget.setWordWrap(True)
                card_layout.addWidget(label_widget)
                card_layout.addWidget(value_widget)
                details_layout.addWidget(card, index // 2, index % 2)
            layout.addLayout(details_layout)

        if information:
            info_card = QFrame(self)
            info_card.setObjectName("informationCard")
            info_layout = QVBoxLayout(info_card)
            info_layout.setContentsMargins(14, 12, 14, 12)
            info_layout.setSpacing(6)

            info_heading = QLabel(
                translate_text("Scenario information", language),
                info_card,
            )
            info_heading.setObjectName("informationHeading")
            info_text = QLabel(information, info_card)
            info_text.setObjectName("informationText")
            info_text.setWordWrap(True)
            info_layout.addWidget(info_heading)
            info_layout.addWidget(info_text)
            layout.addWidget(info_card)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.action_button = QPushButton(
            translate_text(action_text, language),
            self,
        )
        self.action_button.setObjectName("primaryAction")
        self.action_button.setDefault(True)
        self.action_button.clicked.connect(self.accept)
        button_layout.addWidget(self.action_button)
        layout.addLayout(button_layout)

        self.setStyleSheet(
            """
            QDialog {
                background-color: #0f172a;
                color: #e2e8f0;
            }
            QLabel#eyebrow {
                color: #38bdf8;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
            }
            QLabel#dialogHeading {
                color: #f8fafc;
                font-size: 23px;
                font-weight: 700;
            }
            QFrame#metricCard, QFrame#informationCard {
                background-color: #172338;
                border: 1px solid #334155;
                border-radius: 9px;
            }
            QLabel#metricLabel, QLabel#informationHeading {
                color: #94a3b8;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#metricValue {
                color: #f8fafc;
                font-size: 17px;
                font-weight: 700;
            }
            QLabel#informationText {
                color: #e2e8f0;
                font-size: 14px;
            }
            QPushButton#primaryAction {
                background-color: #0891b2;
                border: 1px solid #22d3ee;
                border-radius: 6px;
                color: #f8fafc;
                font-size: 14px;
                font-weight: 700;
                min-width: 130px;
                padding: 9px 16px;
            }
            QPushButton#primaryAction:hover {
                background-color: #0e7490;
            }
            """
        )
        self.adjustSize()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.accept()
            return
        super().keyPressEvent(event)
