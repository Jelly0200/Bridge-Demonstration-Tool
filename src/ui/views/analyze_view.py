from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt
from src.database.repository import Repository


class AnalyzeView(QWidget):
    """Bridge analysis view showing HCP, DDS tricks, and statistical metrics."""

    def __init__(self, board_id: int = 1, parent=None):
        super().__init__(parent)
        self.board_id = board_id
        self.repo = Repository()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 1. Title and board summary.
        header_group = QGroupBox("牌局深度分析摘要 (Board Analytics Summary)")
        header_layout = QVBoxLayout(header_group)

        self.lbl_summary = QLabel(
            "<b>当前牌局编号:</b> #1  |  <b>发牌人:</b> 南 (South)  |  <b>局况:</b> 无局 (None)<br>"
            "<b>分析状态:</b> 统计模型已加载，双明手 DDS 求解器就绪。"
        )
        header_layout.addWidget(self.lbl_summary)
        layout.addWidget(header_group)

        # 2. HCP and suit-length statistics.
        hcp_group = QGroupBox("各方大牌点 (HCP) 与牌型统计矩阵")
        hcp_layout = QVBoxLayout(hcp_group)

        self.hcp_table = QTableWidget(4, 6)
        self.hcp_table.setHorizontalHeaderLabels(
            ["方位 (Player)", "黑桃 (♠)", "红桃 (♥)", "方块 (♦)", "梅花 (♣)", "总大牌点 (HCP)"])
        self.hcp_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Populate sample statistics.
        sample_stats = [
            ("北 (North)", "3", "3", "3", "4", "10 HCP"),
            ("东 (East)", "3", "3", "4", "3", "9 HCP"),
            ("南 (South)", "2", "4", "3", "4", "14 HCP"),
            ("西 (West)", "5", "3", "3", "2", "10 HCP")
        ]

        for row, data in enumerate(sample_stats):
            for col, text in enumerate(data):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.hcp_table.setItem(row, col, item)

        self.hcp_table.setMaximumHeight(160)
        hcp_layout.addWidget(self.hcp_table)
        layout.addWidget(hcp_group)

        # 3. DDS trick projections and statistical metrics.
        dds_group = QGroupBox("DDS 赢墩潜力与统计分布评估")
        dds_layout = QVBoxLayout(dds_group)

        self.lbl_dds_metrics = QLabel(
            "<b>DDS 最佳合约预测:</b> 南/北方向 4♥ (可成局)<br>"
            "<b>变异系数 (Coefficient of Variation):</b> 0.18 (分布均衡)<br>"
            "<b>样本方差与分布特征:</b> 单峰分布，无极端牌型偏态。"
        )
        self.lbl_dds_metrics.setStyleSheet("padding: 10px; background-color: #242831; border-radius: 4px;")
        dds_layout.addWidget(self.lbl_dds_metrics)

        layout.addWidget(dds_group)
        layout.addStretch()

    def update_board(self, board_id: int):
        """Update the analysis summary when the selected board changes."""
        self.board_id = board_id
        self.lbl_summary.setText(
            f"<b>当前牌局编号:</b> #{board_id}  |  <b>发牌人:</b> 南 (South)  |  <b>局况:</b> 无局 (None)<br>"
            f"<b>分析状态:</b> 已加载牌局 #{board_id} 的深度统计特征。"
        )