import sqlite3

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QLabel,
    QVBoxLayout,
)
from PyQt6.QtCore import Qt


class MonitorDialog(QDialog):
    """Show aggregate statistics for every administrator."""

    def __init__(self, repository, current_admin_id, runtime_status, parent=None):
        super().__init__(parent)
        self.repository = repository
        self.current_admin_id = current_admin_id
        self.runtime_status = runtime_status
        self.setWindowTitle("Monitor")
        self.resize(520, 360)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.admin_combo = QComboBox()
        self.administrators = repository.get_administrators()
        for administrator in self.administrators:
            self.admin_combo.addItem(
                administrator["name"],
                administrator["id"],
            )
        self.admin_combo.currentIndexChanged.connect(self._refresh_statistics)
        form.addRow("Administrator:", self.admin_combo)

        self.asset_counts_label = QLabel()
        self.asset_counts_label.setWordWrap(True)
        form.addRow("Asset counts:", self.asset_counts_label)

        self.runtime_label = QLabel(runtime_status.get("runtime", ""))
        self.runtime_label.setWordWrap(True)
        form.addRow("Memory status:", self.runtime_label)

        self.errors_label = QLabel()
        self.errors_label.setWordWrap(True)
        self.errors_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        form.addRow("Application errors:", self.errors_label)
        layout.addLayout(form)

        if self.administrators:
            current_index = self.admin_combo.findData(current_admin_id)
            if current_index >= 0:
                self.admin_combo.setCurrentIndex(current_index)
            self._refresh_statistics()
        else:
            self.admin_combo.setEnabled(False)
            self.asset_counts_label.setText("No administrator accounts.")
        self._refresh_errors()

    def _refresh_statistics(self, _index=None):
        admin_id = self.admin_combo.currentData()
        if admin_id is None:
            return
        try:
            counts = self.repository.get_administrator_asset_counts(admin_id)
        except sqlite3.Error as error:
            self.asset_counts_label.setText(
                f"Unable to read asset counts: {error}"
            )
            return
        self.asset_counts_label.setText(
            "Folders: {folders}    Cases: {cases}    Boards: {boards}\n"
            "Scenarios: {scenarios}    Labels: {labels}".format(**counts)
        )

    def _refresh_errors(self):
        errors = self.runtime_status.get("errors", [])
        self.errors_label.setText(
            "\n".join(errors) if errors else "No recorded errors."
        )
