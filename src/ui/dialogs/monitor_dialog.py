import sqlite3

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
)
from PyQt6.QtCore import Qt


class MonitorDialog(QDialog):
    """Show aggregate statistics for every administrator."""

    ASSET_TYPES = (
        ("folders", "Folders"),
        ("cases", "Cases"),
        ("boards", "Boards"),
        ("scenarios", "Scenarios"),
        ("labels", "Labels"),
    )

    def __init__(self, repository, current_admin_id, runtime_status, parent=None):
        super().__init__(parent)
        self.repository = repository
        self.current_admin_id = current_admin_id
        self.runtime_status = runtime_status
        self.setObjectName("monitorDialog")
        self.setWindowTitle("Monitor")
        self.setMinimumWidth(660)
        self.resize(760, 420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        title = QLabel("System monitor", self)
        title.setObjectName("monitorTitle")
        layout.addWidget(title)

        self.admin_combo = QComboBox()
        self.admin_combo.setObjectName("monitorAdminCombo")
        self.administrators = repository.get_administrators()
        for administrator in self.administrators:
            self.admin_combo.addItem(
                administrator["name"],
                administrator["id"],
            )
        self.admin_combo.currentIndexChanged.connect(self._refresh_statistics)

        administrator_card = QFrame(self)
        administrator_card.setObjectName("monitorCard")
        administrator_layout = QHBoxLayout(administrator_card)
        administrator_layout.setContentsMargins(14, 8, 14, 8)
        administrator_label = QLabel("Administrator:", administrator_card)
        administrator_label.setObjectName("monitorSectionTitle")
        administrator_layout.addWidget(administrator_label)
        administrator_layout.addWidget(self.admin_combo, 1)
        layout.addWidget(administrator_card)

        asset_card = QFrame(self)
        asset_card.setObjectName("monitorCard")
        asset_layout = QVBoxLayout(asset_card)
        asset_layout.setContentsMargins(14, 12, 14, 14)
        asset_layout.setSpacing(8)
        asset_heading = QLabel("Asset counts", asset_card)
        asset_heading.setObjectName("monitorSectionTitle")
        asset_layout.addWidget(asset_heading)

        metrics = QGridLayout()
        metrics.setSpacing(10)
        self.asset_count_labels = {}
        for index, (key, title_text) in enumerate(self.ASSET_TYPES):
            metric = QFrame(asset_card)
            metric.setObjectName("monitorMetric")
            metric_layout = QVBoxLayout(metric)
            metric_layout.setContentsMargins(8, 8, 8, 8)
            metric_layout.setSpacing(2)
            name = QLabel(title_text, metric)
            name.setObjectName("monitorMetricName")
            name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value = QLabel("0", metric)
            value.setObjectName("monitorMetricValue")
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            metric_layout.addWidget(name)
            metric_layout.addWidget(value)
            metric.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )
            metrics.addWidget(metric, 0, index)
            self.asset_count_labels[key] = value
        asset_layout.addLayout(metrics)
        self.empty_state_label = QLabel(
            "No administrator accounts.",
            asset_card,
        )
        self.empty_state_label.setObjectName("monitorEmptyState")
        self.empty_state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state_label.hide()
        asset_layout.addWidget(self.empty_state_label)
        self.asset_error_label = QLabel(asset_card)
        self.asset_error_label.setObjectName("monitorAssetError")
        self.asset_error_label.setWordWrap(True)
        self.asset_error_label.hide()
        asset_layout.addWidget(self.asset_error_label)
        layout.addWidget(asset_card)

        self.asset_counts_label = QLabel()
        self.asset_counts_label.setObjectName("monitorAssetCountsSummary")
        self.asset_counts_label.setVisible(False)

        runtime_card = QFrame(self)
        runtime_card.setObjectName("monitorCard")
        runtime_layout = QVBoxLayout(runtime_card)
        runtime_layout.setContentsMargins(14, 10, 14, 10)
        runtime_layout.setSpacing(6)
        runtime_heading = QLabel("Runtime status", runtime_card)
        runtime_heading.setObjectName("monitorSectionTitle")
        runtime_layout.addWidget(runtime_heading)
        self.runtime_label = QLabel(runtime_status.get("runtime", ""), runtime_card)
        self.runtime_label.setObjectName("monitorRuntimeValue")
        self.runtime_label.setWordWrap(True)
        runtime_layout.addWidget(self.runtime_label)
        errors_card = QFrame(self)
        errors_card.setObjectName("monitorCard")
        errors_layout = QVBoxLayout(errors_card)
        errors_layout.setContentsMargins(14, 10, 14, 10)
        errors_layout.setSpacing(6)
        errors_heading = QLabel("Recent application errors", errors_card)
        errors_heading.setObjectName("monitorSectionTitle")
        errors_layout.addWidget(errors_heading)
        self.errors_label = QLabel(errors_card)
        self.errors_label.setObjectName("monitorErrors")
        self.errors_label.setWordWrap(True)
        self.errors_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        errors_layout.addWidget(self.errors_label)
        status_layout = QHBoxLayout()
        status_layout.setSpacing(10)
        status_layout.addWidget(runtime_card, 1)
        status_layout.addWidget(errors_card, 1)
        layout.addLayout(status_layout)

        self.setStyleSheet(
            """
            QDialog#monitorDialog {
                background: #0f172a;
                color: #e2e8f0;
            }
            QLabel#monitorTitle {
                color: #f8fafc;
                font-size: 26px;
                font-weight: 700;
            }
            QFrame#monitorCard {
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 12px;
            }
            QLabel#monitorSectionTitle {
                color: #e2e8f0;
                font-size: 15px;
                font-weight: 700;
            }
            QFrame#monitorMetric {
                background: #172338;
                border: 1px solid #334155;
                border-radius: 9px;
            }
            QLabel#monitorMetricName {
                color: #94a3b8;
                font-size: 13px;
            }
            QLabel#monitorMetricValue {
                color: #7dd3fc;
                font-size: 26px;
                font-weight: 700;
            }
            QLabel#monitorEmptyState {
                color: #fcd34d;
                font-size: 12px;
            }
            QLabel#monitorAssetError {
                color: #fecaca;
                font-size: 12px;
            }
            QLabel#monitorRuntimeValue, QLabel#monitorErrors {
                color: #cbd5e1;
                font-size: 14px;
                line-height: 1.4;
            }
            QComboBox#monitorAdminCombo {
                min-height: 34px;
                padding: 2px 8px;
                color: #f8fafc;
                background: #0f172a;
                border: 1px solid #475569;
                border-radius: 6px;
                font-size: 14px;
            }
            """
        )

        if self.administrators:
            current_index = self.admin_combo.findData(current_admin_id)
            if current_index >= 0:
                self.admin_combo.setCurrentIndex(current_index)
            self._refresh_statistics()
        else:
            self.admin_combo.setEnabled(False)
            self.asset_counts_label.setText("No administrator accounts.")
            self.empty_state_label.show()
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
            for value in self.asset_count_labels.values():
                value.setText("—")
            self.asset_error_label.setText(
                f"Unable to read asset counts: {error}"
            )
            self.asset_error_label.show()
            return
        self.asset_error_label.hide()
        for key, _title in self.ASSET_TYPES:
            self.asset_count_labels[key].setText(str(counts[key]))
        self.asset_counts_label.setText(
            "Folders: {folders}    Cases: {cases}    Boards: {boards}\n"
            "Scenarios: {scenarios}    Labels: {labels}".format(**counts)
        )

    def _refresh_errors(self):
        errors = self.runtime_status.get("errors", [])
        self.errors_label.setText(
            "\n".join(errors) if errors else "No recorded errors."
        )
