from copy import deepcopy

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from src.robot.label_evaluator import DEFAULT_COLOR_JOBS, LabelEvaluator
from src.ui.i18n import translate_text


class LabelJobsDialog(QDialog):
    """Edit how each label color influences robot card selection."""

    COLORS = ("RED", "ORANGE", "YELLOW", "BLUE", "PURPLE", "GREEN")
    PHASES = (
        ("leading", "Leading"),
        ("following", "Following suit"),
        ("discarding", "Discarding"),
    )
    JOB_CHOICES = (
        ("OFF", "Ignore"),
        ("FIRST", "First sequence in DDS-best group"),
        ("LAST", "Last sequence in DDS-best group"),
        ("OVERRIDE_FIRST", "Override DDS, first sequence"),
        ("OVERRIDE_LAST", "Override DDS, last sequence"),
    )

    def __init__(self, color_jobs=None, language="en", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Define color jobs")
        self.color_jobs = LabelEvaluator.normalize_color_jobs(color_jobs)
        self.job_controls = {}

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Choose how each color affects robot card selection by play phase.",
                self,
            )
        )
        phase_row = QHBoxLayout()
        for phase, title in self.PHASES:
            group = QGroupBox(translate_text(title, language), self)
            grid = QGridLayout(group)
            grid.addWidget(QLabel("Color", group), 0, 0)
            grid.addWidget(QLabel("Job", group), 0, 1)
            for row, color in enumerate(self.COLORS, start=1):
                grid.addWidget(QLabel(color, group), row, 0)
                choice = QComboBox(group)
                for job, text in self.JOB_CHOICES:
                    choice.addItem(text, job)
                current_job = self.color_jobs[phase][color]
                choice.setCurrentIndex(
                    choice.findData(current_job)
                )
                grid.addWidget(choice, row, 1)
                self.job_controls[phase, color] = choice
            phase_row.addWidget(group)
        layout.addLayout(phase_row)

        buttons = QHBoxLayout()
        self.restore_button = QPushButton("Restore defaults", self)
        self.restore_button.clicked.connect(self._restore_defaults)
        buttons.addWidget(self.restore_button)
        buttons.addStretch()
        self.apply_button = QPushButton("Apply", self)
        self.apply_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.clicked.connect(self.reject)
        buttons.addWidget(self.apply_button)
        buttons.addWidget(self.cancel_button)
        layout.addLayout(buttons)
        self.resize(1050, 420)

    def accept(self):
        self.color_jobs = {
            phase: {
                color: self.job_controls[phase, color].currentData()
                for color in self.COLORS
            }
            for phase, _title in self.PHASES
        }
        super().accept()

    def _restore_defaults(self):
        for phase, _title in self.PHASES:
            for color in self.COLORS:
                choice = self.job_controls[phase, color]
                choice.setCurrentIndex(
                    choice.findData(DEFAULT_COLOR_JOBS[phase][color])
                )


class LabelDefinitionDialog(QDialog):
    """Show the current label-color jobs without exposing editing controls."""

    COLOR_VALUES = {
        "RED": "#ef4444",
        "ORANGE": "#f97316",
        "YELLOW": "#eab308",
        "BLUE": "#3b82f6",
        "PURPLE": "#a855f7",
        "GREEN": "#22c55e",
    }
    JOB_DESCRIPTIONS = {
        "OFF": "Ignore",
        "FIRST": "First label sequence among DDS-best cards",
        "LAST": "Last label sequence among DDS-best cards",
        "OVERRIDE_FIRST": "Override DDS: first label sequence",
        "OVERRIDE_LAST": "Override DDS: last label sequence",
    }

    def __init__(self, color_jobs=None, language="en", parent=None):
        super().__init__(parent)
        self.setWindowTitle(translate_text("Label definitions", language))
        jobs = LabelEvaluator.normalize_color_jobs(color_jobs)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)
        self.sequence_rows = []
        colors = LabelJobsDialog.COLORS
        phases = LabelJobsDialog.PHASES
        self.matrix = QTableWidget(len(phases), len(colors), self)
        self.matrix.setHorizontalHeaderLabels(
            [translate_text(color.title(), language) for color in colors]
        )
        for column, color in enumerate(colors):
            self.matrix.horizontalHeaderItem(column).setForeground(
                QColor(self.COLOR_VALUES[color])
            )
        self.matrix.setVerticalHeaderLabels(
            [
                translate_text(phase_title, language)
                for _phase, phase_title in phases
            ]
        )
        self.matrix.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.matrix.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        self.matrix.setWordWrap(True)
        self.matrix.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.matrix.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.matrix.verticalHeader().setMinimumWidth(125)
        for row, (phase, _phase_title) in enumerate(phases):
            ordered_colors = LabelEvaluator.COLOR_PRIORITY[phase]
            for priority, color in enumerate(ordered_colors, start=1):
                self.sequence_rows.append(
                    (phase, priority, color, jobs[phase][color])
                )
            for column, color in enumerate(colors):
                priority = ordered_colors.index(color) + 1
                job = jobs[phase][color]
                description = translate_text(
                    self.JOB_DESCRIPTIONS[job],
                    language,
                )
                item = QTableWidgetItem(f"{priority}. {description}")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setForeground(QColor("#cbd5e1"))
                self.matrix.setItem(row, column, item)
        self.matrix.setMinimumHeight(300)
        layout.addWidget(self.matrix, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close,
            parent=self,
        )
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
        self.setStyleSheet(
            """
            QDialog {
                background-color: #0f172a;
                color: #e2e8f0;
            }
            QTableWidget {
                background-color: #111827;
                gridline-color: #334155;
                border: 1px solid #334155;
            }
            QHeaderView::section {
                background-color: #1e293b;
                padding: 6px;
                border: 1px solid #334155;
                font-weight: 700;
            }
            """
        )
        self.resize(1120, 480)
