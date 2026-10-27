import statistics
from collections import defaultdict

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.generate_test_report import generate_pdf_report
from src.ui.i18n import show_message, translate_text


class TestReportDialog(QDialog):
    """Present administrator-wide test performance and scenario difficulty."""

    def __init__(
        self,
        repository,
        admin_id: int,
        language: str = "en",
        parent=None,
    ):
        super().__init__(parent)
        self.language = language
        self.report_data = repository.get_test_report_data(admin_id)
        self.setWindowTitle(translate_text("Test report", self.language))
        self.resize(1280, 850)
        self.setMinimumSize(900, 600)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        content = QWidget(scroll)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        self.stats_labels = self._build_overall_section(layout)
        self.ability_table = self._build_ability_section(layout)
        self.scenario_table = self._build_difficulty_section(layout)
        self.top_three_table = self._build_top_three_section(layout)
        layout.addStretch()

        scroll.setWidget(content)
        outer_layout = QVBoxLayout(self)
        outer_layout.addWidget(scroll)
        footer = QHBoxLayout()
        footer.addStretch()
        self.export_pdf_button = QPushButton(
            translate_text("Export PDF", self.language),
            self,
        )
        self.export_pdf_button.clicked.connect(self._export_pdf)
        footer.addWidget(self.export_pdf_button)
        self.close_button = QPushButton(
            translate_text("Close", self.language),
            self,
        )
        self.close_button.clicked.connect(self.accept)
        footer.addWidget(self.close_button)
        outer_layout.addLayout(footer)

    def _export_pdf(self):
        filename, _selected_filter = QFileDialog.getSaveFileName(
            self,
            translate_text("Save test report", self.language),
            "test-report.pdf",
            translate_text("PDF files (*.pdf)", self.language),
        )
        if not filename:
            return
        if not filename.lower().endswith(".pdf"):
            filename = f"{filename}.pdf"
        try:
            generate_pdf_report(self.report_data, filename, self.language)
        except (ImportError, OSError, RuntimeError, ValueError) as error:
            show_message(
                self,
                "critical",
                "Unable to generate test report",
                str(error),
            )
            return
        show_message(
            self,
            "information",
            "Test report generated",
            f"Report saved to: {filename}",
        )

    def _section(self, title: str, parent_layout):
        group = QGroupBox(translate_text(title, self.language), self)
        group_layout = QVBoxLayout(group)
        parent_layout.addWidget(group)
        return group_layout

    @staticmethod
    def _format_score(value):
        if value is None:
            return "—"
        return f"{value:.2f}" if isinstance(value, float) else str(value)

    def _build_overall_section(self, layout):
        section = self._section("Overall statistics", layout)
        stats_layout = QGridLayout()
        section.addLayout(stats_layout)

        results = self.report_data["results"]
        scores = [int(result["score"]) for result in results]
        unique_contestants = {
            result["student_id"]
            if result["student_id"] is not None
            else result["student_name"]
            for result in results
        }
        mean_score = statistics.mean(scores) if scores else None
        median_score = statistics.median(scores) if scores else None
        population_stddev = statistics.pstdev(scores) if scores else None
        values = (
            ("Administrator", self.report_data["administrator"]),
            ("Tests", str(len(self.report_data["tests"]))),
            ("Test attempts", str(len(results))),
            ("Contestants", str(len(unique_contestants))),
            ("Total score", str(sum(scores))),
            (
                "Average score",
                self._format_score(float(mean_score))
                if mean_score is not None
                else "—",
            ),
            (
                "Mean score",
                self._format_score(float(mean_score))
                if mean_score is not None
                else "—",
            ),
            (
                "Median score",
                self._format_score(float(median_score))
                if median_score is not None
                else "—",
            ),
            ("Maximum score", self._format_score(max(scores) if scores else None)),
            ("Minimum score", self._format_score(min(scores) if scores else None)),
            ("Score standard deviation", self._format_score(population_stddev)),
        )
        value_labels = {}
        for index, (label, value) in enumerate(values):
            row, column = divmod(index, 3)
            key_label = QLabel(translate_text(label, self.language))
            key_label.setStyleSheet("font-weight: 600; color: #94a3b8;")
            value_label = QLabel(value)
            value_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            value_label.setStyleSheet("font-size: 17px; font-weight: 700;")
            stats_layout.addWidget(key_label, row, column * 2)
            stats_layout.addWidget(value_label, row, column * 2 + 1)
            value_labels[label] = value_label
        return value_labels

    def _build_ability_section(self, layout):
        section = self._section("Contestant ability by problem", layout)
        table = QTableWidget(section.parentWidget())
        table.setObjectName("test_report_ability_matrix")
        table.setProperty("bilingualExempt", True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)

        problem_columns = []
        for test in self.report_data["tests"]:
            for index, problem in enumerate(test["problems"], start=1):
                problem_columns.append(
                    (
                        test["id"],
                        int(problem.get("sequence", index)),
                        test["name"],
                    )
                )
        problem_columns.sort(key=lambda item: (item[0], item[1]))
        header_labels = [
            translate_text("Student ID", self.language),
            translate_text("Contestant", self.language),
        ]
        header_labels.extend(
            f"{test_name}\n"
            f"{translate_text('Problem ', self.language)}{sequence}"
            for _, sequence, test_name in problem_columns
        )
        table.setColumnCount(len(header_labels))
        table.setHorizontalHeaderLabels(header_labels)

        contestants = {}
        score_by_cell = {}
        for result in self.report_data["results"]:
            contestant_key = (
                ("id", result["student_id"])
                if result["student_id"] is not None
                else ("name", result["student_name"])
            )
            contestants.setdefault(
                contestant_key,
                {
                    "student_id": result["student_id"],
                    "student_name": result["student_name"],
                },
            )
            problem_results = result["contracts"]
            if not isinstance(problem_results, list):
                raise ValueError(
                    f"Test result {result['id']} has invalid problem data."
                )
            for index, problem_result in enumerate(problem_results, start=1):
                if not isinstance(problem_result, dict):
                    raise ValueError(
                        f"Test result {result['id']} has invalid problem data."
                    )
                problem_number = int(problem_result.get("problem_number", index))
                score_by_cell.setdefault(
                    (
                        contestant_key,
                        result["test_id"],
                        problem_number,
                    ),
                    int(problem_result["score"]),
                )

        sorted_contestants = sorted(
            contestants.items(),
            key=lambda item: (
                (item[1]["student_name"] or "").casefold(),
                item[1]["student_id"] or 0,
            ),
        )
        table.setRowCount(len(sorted_contestants))
        for row, (contestant_key, contestant) in enumerate(sorted_contestants):
            self._set_item(
                table,
                row,
                0,
                str(contestant["student_id"] or ""),
                right_aligned=False,
            )
            self._set_item(
                table,
                row,
                1,
                contestant["student_name"] or "",
                right_aligned=False,
            )
            for column, (test_id, sequence, _test_name) in enumerate(
                problem_columns,
                start=2,
            ):
                value = score_by_cell.get(
                    (contestant_key, test_id, sequence)
                )
                self._set_item(
                    table,
                    row,
                    column,
                    self._format_score(value),
                )

        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setMinimumHeight(190)
        section.addWidget(table)
        return table

    def _build_difficulty_section(self, layout):
        section = self._section("Scenario difficulty", layout)
        table = QTableWidget(section.parentWidget())
        table.setObjectName("test_report_scenario_difficulty")
        table.setProperty("bilingualExempt", True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        headers = [
            "Scenario",
            "Average score",
            "Mean score",
            "Median score",
            "Count",
            "Maximum score",
            "Minimum score",
            "Score standard deviation",
        ]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(
            [translate_text(header, self.language) for header in headers]
        )

        candidate_scenarios = {}
        for test in self.report_data["tests"]:
            for problem in test["problems"]:
                for scenario_id in problem["scenario_ids"]:
                    candidate_scenarios.setdefault(int(scenario_id), None)

        scenario_scores = defaultdict(list)
        for result in self.report_data["results"]:
            problem_results = result["contracts"]
            if not isinstance(problem_results, list):
                raise ValueError(
                    f"Test result {result['id']} has invalid problem data."
                )
            for problem_result in problem_results:
                if not isinstance(problem_result, dict):
                    raise ValueError(
                        f"Test result {result['id']} has invalid problem data."
                    )
                scenario_id = int(problem_result["scenario_id"])
                candidate_scenarios.setdefault(scenario_id, None)
                scenario_scores[scenario_id].append(int(problem_result["score"]))

        scenarios = self.report_data["scenarios"]
        rows = []
        for scenario_id in candidate_scenarios:
            scenario = scenarios.get(scenario_id)
            if scenario is None:
                label = f"Scenario #{scenario_id}"
            else:
                parts = [
                    scenario["case_name"],
                    scenario["board_name"],
                    scenario["name"],
                ]
                label = " / ".join(part for part in parts if part)
            scores = scenario_scores[scenario_id]
            mean_score = float(statistics.mean(scores)) if scores else None
            median_score = float(statistics.median(scores)) if scores else None
            stddev = statistics.pstdev(scores) if scores else None
            rows.append(
                (
                    label,
                    mean_score,
                    mean_score,
                    median_score,
                    len(scores),
                    max(scores) if scores else None,
                    min(scores) if scores else None,
                    stddev,
                )
            )
        rows.sort(key=lambda row: row[0].casefold())
        table.setRowCount(len(rows))
        for row_index, values in enumerate(rows):
            for column, value in enumerate(values):
                self._set_item(
                    table,
                    row_index,
                    column,
                    str(value)
                    if column == 4
                    else self._format_score(value),
                    right_aligned=column > 0,
                )
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setMinimumHeight(190)
        section.addWidget(table)
        return table

    def _build_top_three_section(self, layout):
        section = self._section("Top three contestants", layout)
        table = QTableWidget(section.parentWidget())
        table.setObjectName("test_report_top_three")
        table.setProperty("bilingualExempt", True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        headers = ["Rank", "Student ID", "Contestant", "Test", "Score"]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(
            [translate_text(header, self.language) for header in headers]
        )

        best_by_contestant = {}
        for result in self.report_data["results"]:
            contestant_key = (
                ("id", result["student_id"])
                if result["student_id"] is not None
                else ("name", result["student_name"])
            )
            score = int(result["score"])
            current = best_by_contestant.get(contestant_key)
            if current is None or score > int(current["score"]):
                best_by_contestant[contestant_key] = result
        top_three = sorted(
            best_by_contestant.values(),
            key=lambda result: (
                -int(result["score"]),
                (result["student_name"] or "").casefold(),
                result["submitted_at"] or "",
            ),
        )[:3]
        table.setRowCount(len(top_three))
        for row, result in enumerate(top_three, start=1):
            values = (
                str(row),
                str(result["student_id"] or ""),
                result["student_name"] or "",
                result["test_name"],
                str(result["score"]),
            )
            for column, value in enumerate(values):
                self._set_item(
                    table,
                    row - 1,
                    column,
                    value,
                    right_aligned=column in {0, 1, 4},
                )
        if not top_three:
            section.addWidget(
                QLabel(translate_text("No submissions yet.", self.language))
            )
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setMinimumHeight(120)
        section.addWidget(table)
        return table

    @staticmethod
    def _set_item(table, row, column, value, right_aligned=True):
        item = QTableWidgetItem(value)
        item.setTextAlignment(
            Qt.AlignmentFlag.AlignVCenter
            | (
                Qt.AlignmentFlag.AlignRight
                if right_aligned
                else Qt.AlignmentFlag.AlignLeft
            )
        )
        table.setItem(row, column, item)
