from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox
)
from PyQt6.QtCore import Qt


class DdsPanel(QWidget):
    """DDS panel displaying projected tricks for each direction and strain."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Panel heading.
        group = QGroupBox("DDS 双明手预测赢墩矩阵 (Double Dummy Solver)")
        group_layout = QVBoxLayout(group)

        self.lbl_desc = QLabel("<b>提示：</b>下表展示了四方作为庄家时，在各花色/无王定约下的极限可赢取墩数。")
        group_layout.addWidget(self.lbl_desc)

        # Rows represent directions; columns represent strains.
        self.table = QTableWidget(4, 5)
        self.table.setHorizontalHeaderLabels(["♠ (S)", "♥ (H)", "♦ (D)", "♣ (C)", "NT"])
        self.table.setVerticalHeaderLabels(["北 (North)", "东 (East)", "南 (South)", "西 (West)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Populate sample DDS results.
        sample_dds_data = [
            ["8", "10", "7", "7", "9"],  # North
            ["5", "3", "6", "6", "4"],  # East
            ["8", "10", "7", "7", "9"],  # South
            ["5", "3", "6", "6", "4"]  # West
        ]

        for row, row_data in enumerate(sample_dds_data):
            for col, val in enumerate(row_data):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # Highlight results that may make game.
                if int(val) >= 9:
                    item.setStyleSheet("color: #2ecc71; font-weight: bold;")
                self.table.setItem(row, col, item)

        self.table.setMaximumHeight(180)
        group_layout.addWidget(self.table)

        layout.addWidget(group)
        layout.addStretch()

    def update_dds_results(self, dds_matrix: dict):
        """Update the displayed DDS results."""
        # Connect this method to DdsWrapper results when live analysis is integrated.
        pass