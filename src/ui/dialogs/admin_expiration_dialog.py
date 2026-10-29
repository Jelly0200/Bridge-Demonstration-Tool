from datetime import date
from typing import Optional

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QVBoxLayout,
)


class AdminExpirationDialog(QDialog):
    def __init__(
        self,
        expires_on: Optional[str] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("My account expiration")

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.never_expires_checkbox = QCheckBox("This account does not expire")
        self.expiration_date = QDateEdit(self)
        self.expiration_date.setCalendarPopup(True)
        self.expiration_date.setDisplayFormat("yyyy-MM-dd")
        self.expiration_date.setMinimumDate(QDate.currentDate())
        self.expiration_date.setDate(QDate.currentDate())
        if expires_on is not None:
            expiration = date.fromisoformat(expires_on)
            self.expiration_date.setDate(
                QDate(expiration.year, expiration.month, expiration.day)
            )
        self.never_expires_checkbox.setChecked(expires_on is None)
        self.never_expires_checkbox.toggled.connect(
            self.expiration_date.setDisabled
        )
        form.addRow("Expiration date:", self.expiration_date)
        layout.addLayout(form)
        layout.addWidget(self.never_expires_checkbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.expiration_date.setDisabled(expires_on is None)

    def selected_expiration_date(self) -> Optional[date]:
        if self.never_expires_checkbox.isChecked():
            return None
        return self.expiration_date.date().toPyDate()
