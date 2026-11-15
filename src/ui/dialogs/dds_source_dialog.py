from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from src.core.dds_wrapper import (
    DDS_PROVIDERS,
    DdsWrapper,
)
from src.ui.i18n import translate_text


class DdsSourceDialog(QDialog):
    PROVIDER_LABELS = {
        "none": "A. No DDS",
        "dds3": "B. Registered DDS (last registered folder)",
        "scanned": "C. Scan the DDS source folder",
        "endplay": "D. Endplay (bundled DDS)",
    }
    PROVIDER_DESCRIPTIONS = {
        "none": "Turn off DDS features without affecting the rest of the app.",
        "dds3": "Load the DDS extension from its last registered folder.",
        "scanned": (
            "Search the selected folder for a built native DDS module "
            "and use it when found."
        ),
        "endplay": "Use the DDS library bundled with Endplay.",
    }

    def __init__(
        self,
        selected_provider: str = "none",
        parent=None,
        *,
        source_folder: str | None = None,
        registered_source_folder: str | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("ddsSourceDialog")
        self.setWindowTitle("DDS source")
        self.setMinimumWidth(500)
        self.language = getattr(parent, "language", "en")
        self.source_folder = (
            source_folder
            or str(DdsWrapper.normalize_source_folder(None))
        )
        self.registered_source_folder = (
            str(DdsWrapper.normalize_source_folder(registered_source_folder))
            if registered_source_folder
            else None
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)
        title = QLabel("Choose a DDS source", self)
        title.setObjectName("ddsSourceTitle")
        layout.addWidget(title)
        description = QLabel(
            "Choose one provider, or leave DDS turned off.",
            self,
        )
        description.setObjectName("ddsSourceDescription")
        description.setWordWrap(True)
        layout.addWidget(description)

        self.provider_buttons: dict[str, QRadioButton] = {}
        self.provider_cards: dict[str, QFrame] = {}
        self.provider_status_labels: dict[str, QLabel] = {}
        self.dds_source_folder_input: QLineEdit | None = None
        self.provider_group = QButtonGroup(self)
        self.provider_group.setExclusive(True)
        for provider in DDS_PROVIDERS:
            card = QFrame(self)
            card.setObjectName("ddsSourceOption")
            card.setProperty("selected", provider == selected_provider)
            row = QVBoxLayout(card)
            row.setContentsMargins(14, 12, 14, 12)
            row.setSpacing(6)

            button = QRadioButton(self.PROVIDER_LABELS[provider], card)
            button.setObjectName(f"provider_option_{provider}")
            button.setChecked(provider == selected_provider)
            button.setProperty("ddsProvider", provider)
            button.toggled.connect(self._refresh_option_styles)
            self.provider_group.addButton(button)
            row.addWidget(button)

            details = QVBoxLayout()
            details.setContentsMargins(28, 0, 0, 0)
            detail_label = QLabel(
                self.PROVIDER_DESCRIPTIONS[provider],
                card,
            )
            detail_label.setObjectName("ddsSourceDetail")
            detail_label.setWordWrap(True)
            details.addWidget(detail_label)
            if provider == "scanned":
                source_path_label = QLabel("DDS source folder", card)
                source_path_label.setObjectName("ddsSourceFolderLabel")
                details.addWidget(source_path_label)
                source_path_row = QHBoxLayout()
                source_folder_input = QLineEdit(
                    self.source_folder,
                    card,
                )
                source_folder_input.setObjectName("ddsSourceFolderInput")
                source_folder_input.textChanged.connect(
                    self._refresh_scanned_status
                )
                browse_button = QPushButton("Browse...", card)
                browse_button.setObjectName("browseDdsSourceFolder")
                browse_button.clicked.connect(self._browse_dds_source_folder)
                source_path_row.addWidget(source_folder_input, 1)
                source_path_row.addWidget(browse_button)
                details.addLayout(source_path_row)
                self.dds_source_folder_input = source_folder_input
            if provider != "none":
                status_text = (
                    "Installed"
                    if self._is_provider_available(provider)
                    else "Not installed"
                )
                status = QLabel(status_text, card)
                status.setObjectName(f"provider_status_{provider}")
                status.setProperty("installed", status_text == "Installed")
                if provider == "dds3":
                    status.setToolTip(
                        self.registered_source_folder
                        or "No DDS source folder is registered."
                    )
                details.addWidget(status, alignment=Qt.AlignmentFlag.AlignLeft)
                self.provider_status_labels[provider] = status
            row.addLayout(details)
            layout.addWidget(card)
            self.provider_buttons[provider] = button
            self.provider_cards[provider] = card

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setStyleSheet(
            """
            QDialog#ddsSourceDialog {
                background: #0f172a;
                color: #e2e8f0;
            }
            QLabel#ddsSourceTitle {
                color: #f8fafc;
                font-size: 22px;
                font-weight: 700;
            }
            QLabel#ddsSourceDescription, QLabel#ddsSourceDetail {
                color: #94a3b8;
                font-size: 12px;
            }
            QFrame#ddsSourceOption {
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 10px;
            }
            QFrame#ddsSourceOption[selected="true"] {
                background: #172b3f;
                border: 1px solid #38bdf8;
            }
            QRadioButton {
                color: #f1f5f9;
                font-size: 14px;
                font-weight: 600;
                spacing: 9px;
            }
            QLabel#provider_status_dds3,
            QLabel#provider_status_scanned,
            QLabel#provider_status_endplay {
                padding: 3px 8px;
                background: #14532d;
                color: #bbf7d0;
                border-radius: 8px;
                font-size: 11px;
                font-weight: 700;
            }
            QLabel#provider_status_dds3[installed="false"],
            QLabel#provider_status_scanned[installed="false"],
            QLabel#provider_status_endplay[installed="false"] {
                background: #7f1d1d;
                color: #fecaca;
            }
            QDialogButtonBox QPushButton {
                min-width: 84px;
                min-height: 30px;
                padding: 2px 10px;
                border: 1px solid #475569;
                border-radius: 6px;
                color: #e2e8f0;
                background: #1e293b;
            }
            QDialogButtonBox QPushButton:hover {
                background: #334155;
            }
            QPushButton#browseDdsSourceFolder {
                min-width: 92px;
                min-height: 28px;
                padding: 2px 8px;
                border: 1px solid #475569;
                border-radius: 6px;
                color: #e2e8f0;
                background: #1e293b;
            }
            """
        )
        self._refresh_option_styles()

    def selected_source_folder(self) -> str:
        if self.dds_source_folder_input is None:
            return ""
        folder = self.dds_source_folder_input.text().strip()
        if not folder:
            return ""
        return str(DdsWrapper.normalize_source_folder(folder))

    def selected_provider(self) -> str:
        for provider, button in self.provider_buttons.items():
            if button.isChecked():
                return provider
        return "none"

    def _is_provider_available(self, provider: str) -> bool:
        if provider == "scanned":
            if not self.selected_source_folder():
                return False
            return DdsWrapper.is_provider_installed(
                provider,
                self.selected_source_folder(),
            )
        if provider == "dds3":
            if not self.registered_source_folder:
                return False
            return DdsWrapper.is_provider_installed(
                provider,
                self.registered_source_folder,
            )
        return DdsWrapper.is_provider_installed(provider)

    def _refresh_scanned_status(self, *_):
        status = self.provider_status_labels.get("scanned")
        if status is None:
            return
        installed = self._is_provider_available("scanned")
        status.setText("Installed" if installed else "Not installed")
        status.setProperty("installed", installed)
        style = status.style()
        if style is not None:
            style.unpolish(status)
            style.polish(status)

    def _browse_dds_source_folder(self, *_):
        if self.dds_source_folder_input is None:
            return
        folder = QFileDialog.getExistingDirectory(
            self,
            translate_text("Choose DDS source folder", self.language),
            self.selected_source_folder(),
        )
        if folder:
            self.dds_source_folder_input.setText(folder)

    def _refresh_option_styles(self):
        for provider, card in self.provider_cards.items():
            card.setProperty(
                "selected",
                self.provider_buttons[provider].isChecked(),
            )
            card.style().unpolish(card)
            card.style().polish(card)
