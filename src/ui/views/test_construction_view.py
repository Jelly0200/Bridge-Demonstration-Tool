import re
import sqlite3

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.database.repository import Repository
from src.ui.i18n import (
    BilingualTextController,
    exec_and_delete,
    show_message,
    translate_text,
)


DEFAULT_STASIS = ["=", "-1", "-2", "+1", "+2"]


class TestProblemDialog(QDialog):
    """Configure one case-based problem and its contract/stasis score matrix."""

    def __init__(
        self,
        assets: dict,
        problem: dict | None = None,
        language_controller: BilingualTextController | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.assets = assets
        self.language_controller = language_controller
        self.problem = None
        self.setWindowTitle("Test problem")
        self.resize(760, 650)
        self._build_ui()
        if problem:
            self._load_problem(problem)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.case_combo = QComboBox()
        for case in self.assets["cases"]:
            self.case_combo.addItem(case["name"], case["id"])
        form.addRow("Case:", self.case_combo)
        layout.addLayout(form)

        layout.addWidget(
            QLabel(
                "Possible scenarios (one will be selected per test run):"
            )
        )
        self.scenario_list = QListWidget()
        self.scenario_list.setMinimumHeight(130)
        self.scenario_list.setMaximumHeight(190)
        layout.addWidget(self.scenario_list)

        stasis_layout = QHBoxLayout()
        stasis_layout.addWidget(QLabel("Acceptable result stasis:"))
        self.stasis_list = QListWidget()
        self.stasis_list.setMaximumHeight(100)
        stasis_layout.addWidget(self.stasis_list, 1)
        stasis_buttons = QVBoxLayout()
        self.add_stasis_button = QPushButton("Add stasis")
        self.add_stasis_button.clicked.connect(self._add_stasis)
        stasis_buttons.addWidget(self.add_stasis_button)
        self.remove_stasis_button = QPushButton("Remove selected stasis")
        self.remove_stasis_button.clicked.connect(self._remove_stasis)
        stasis_buttons.addWidget(self.remove_stasis_button)
        stasis_buttons.addStretch()
        stasis_layout.addLayout(stasis_buttons)
        layout.addLayout(stasis_layout)

        layout.addWidget(
            QLabel(
                "Each scenario has its own scoring rule, even when scenarios "
                "share the same contract. Enter a score for every scenario and stasis."
            )
        )
        self.contract_status_label = QLabel()
        layout.addWidget(self.contract_status_label)
        self.matrix = QTableWidget(0, 0)
        self.matrix.setEditTriggers(
            QAbstractItemView.EditTrigger.AllEditTriggers
        )
        self.matrix.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.matrix.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.matrix.setMinimumHeight(190)
        layout.addWidget(self.matrix, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept_problem)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.case_combo.currentIndexChanged.connect(self._populate_scenarios)
        self.scenario_list.itemChanged.connect(self._refresh_matrix)
        self._populate_scenarios()
        self._set_stasis(DEFAULT_STASIS)

    def _populate_scenarios(self, _index=None, *, selected_ids=None):
        self.scenario_list.blockSignals(True)
        self.scenario_list.clear()
        case_id = self.case_combo.currentData()
        for scenario in self.assets["scenarios"]:
            if scenario["case_id"] != case_id:
                continue
            contract = scenario["contract"] or "No final contract"
            item = QListWidgetItem(
                f"{scenario['name']} — {contract}",
                self.scenario_list,
            )
            item.setData(Qt.ItemDataRole.UserRole, scenario["id"])
            checked = selected_ids is None or scenario["id"] in selected_ids
            item.setCheckState(
                Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
            )
        self.scenario_list.blockSignals(False)
        self._refresh_matrix()

    def _selected_scenarios(self):
        selected_ids = {
            self.scenario_list.item(index).data(Qt.ItemDataRole.UserRole)
            for index in range(self.scenario_list.count())
            if self.scenario_list.item(index).checkState()
            == Qt.CheckState.Checked
        }
        return [
            scenario
            for scenario in self.assets["scenarios"]
            if scenario["id"] in selected_ids
        ]

    def _derived_contracts(self):
        contracts = []
        for _scenario_id, _scenario_name, contract in self._scenario_rows():
            if contract not in contracts:
                contracts.append(contract)
        return contracts

    def _scenario_rows(self):
        rows = []
        for scenario in self._selected_scenarios():
            contract = scenario["contract"].strip().upper()
            if not contract:
                raise ValueError(
                    f"{scenario['name']} has no final contract. "
                    "Complete and save its auction first."
                )
            rows.append((scenario["id"], scenario["name"], contract))
        return rows

    def _current_scores(self):
        scores = {}
        stasis = [
            self.matrix.horizontalHeaderItem(column).text()
            for column in range(self.matrix.columnCount())
            if self.matrix.horizontalHeaderItem(column)
        ]
        for row in range(self.matrix.rowCount()):
            header = self.matrix.verticalHeaderItem(row)
            if header is None:
                continue
            metadata = header.data(Qt.ItemDataRole.UserRole)
            if not metadata:
                continue
            scenario_id, contract = metadata
            scores[scenario_id] = {contract: {}}
            for column, result in enumerate(stasis):
                item = self.matrix.item(row, column)
                scores[scenario_id][contract][result] = (
                    item.text() if item else "0"
                )
        return scores

    def _refresh_matrix(self, *_args, scores=None):
        self._commit_active_matrix_edit()
        previous_scores = scores if scores is not None else self._current_scores()
        scenario_rows = []
        warning = ""
        try:
            scenario_rows = self._scenario_rows()
        except ValueError as error:
            warning = str(error)
        if not scenario_rows and not warning:
            warning = "Select at least one scenario from the case."
        language = (
            self.language_controller.language
            if self.language_controller is not None
            else "en"
        )
        self.contract_status_label.setText(translate_text(warning, language))
        stasis = self._stasis_values()
        self.matrix.setRowCount(len(scenario_rows))
        self.matrix.setColumnCount(len(stasis))
        for column, result in enumerate(stasis):
            self.matrix.setHorizontalHeaderItem(
                column,
                QTableWidgetItem(result),
            )
        for row, (scenario_id, scenario_name, contract) in enumerate(
            scenario_rows
        ):
            scenario_scores = previous_scores.get(scenario_id)
            if not isinstance(scenario_scores, dict):
                scenario_scores = previous_scores.get(str(scenario_id), {})
            contract_scores = scenario_scores.get(contract)
            if not isinstance(contract_scores, dict):
                contract_scores = previous_scores.get(contract, {})
            self.matrix.setVerticalHeaderItem(
                row,
                QTableWidgetItem(
                    f"{scenario_name} — {contract} (#{scenario_id})"
                ),
            )
            self.matrix.verticalHeaderItem(row).setData(
                Qt.ItemDataRole.UserRole,
                (scenario_id, contract),
            )
            for column, result in enumerate(stasis):
                value = contract_scores.get(result, "0")
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFlags(
                    item.flags() | Qt.ItemFlag.ItemIsEditable
                )
                self.matrix.setItem(
                    row,
                    column,
                    item,
                )

    def _commit_active_matrix_edit(self):
        focused_widget = self.matrix.focusWidget()
        viewport = self.matrix.viewport()
        if (
            focused_widget is None
            or focused_widget is self.matrix
            or viewport is None
            or not viewport.isAncestorOf(focused_widget)
        ):
            return

        editor = focused_widget
        while editor.parentWidget() is not viewport:
            parent = editor.parentWidget()
            if parent is None:
                return
            editor = parent

        index = self.matrix.indexAt(editor.geometry().center())
        delegate = self.matrix.itemDelegate()
        if index.isValid() and delegate is not None:
            delegate.setModelData(
                editor,
                self.matrix.model(),
                index,
            )

    def _stasis_values(self):
        return [
            self.stasis_list.item(index).text()
            for index in range(self.stasis_list.count())
        ]

    def _set_stasis(self, stasis_values):
        self.stasis_list.clear()
        for value in stasis_values:
            self.stasis_list.addItem(value)
        self._refresh_matrix()

    @staticmethod
    def _normalize_stasis(value: str) -> str:
        normalized = value.strip()
        if normalized == "=":
            return normalized
        if not re.fullmatch(r"[+-](?:[1-9]|1[0-3])", normalized):
            raise ValueError("Use = or a signed trick difference from -13 to +13.")
        return normalized

    def _add_stasis(self):
        language = (
            self.language_controller.language
            if self.language_controller is not None
            else "en"
        )
        value, accepted = QInputDialog.getText(
            self,
            translate_text("Add stasis", language),
            translate_text(
                "Enter = or a signed trick difference (for example +3):",
                language,
            ),
        )
        if not accepted:
            return
        try:
            value = self._normalize_stasis(value)
        except ValueError as error:
            show_message(self, "warning", "Invalid stasis", str(error))
            return
        if value in self._stasis_values():
            show_message(
                self,
                "warning",
                "Duplicate stasis",
                "That stasis is already listed.",
            )
            return
        values = self._stasis_values()
        values.append(value)
        self._set_stasis(values)

    def _remove_stasis(self):
        row = self.stasis_list.currentRow()
        if row < 0:
            return
        values = self._stasis_values()
        values.pop(row)
        self._set_stasis(values)

    def _load_problem(self, problem):
        case_index = self.case_combo.findData(problem.get("case_id"))
        if case_index >= 0:
            self.case_combo.setCurrentIndex(case_index)
        scenario_ids = set(problem.get("scenario_ids", []))
        self._populate_scenarios(selected_ids=scenario_ids)
        self._set_stasis(problem.get("results") or DEFAULT_STASIS)
        self._refresh_matrix(
            scores=(
                problem.get("scenario_scores")
                or problem.get("scores")
                or {}
            )
        )

    def _problem_data(self):
        self._commit_active_matrix_edit()
        case_id = self.case_combo.currentData()
        if case_id is None:
            raise ValueError("Choose a case for this problem.")
        scenario_rows = self._scenario_rows()
        scenario_ids = [scenario_id for scenario_id, _, _ in scenario_rows]
        if not scenario_ids:
            raise ValueError("Select at least one scenario from the case.")
        contracts = self._derived_contracts()
        if not contracts:
            raise ValueError("Select scenarios with saved final contracts.")

        stasis = self._stasis_values()
        if not stasis:
            raise ValueError("Add at least one acceptable result stasis.")
        normalized_stasis = [self._normalize_stasis(value) for value in stasis]
        if len(normalized_stasis) != len(set(normalized_stasis)):
            raise ValueError("Result stasis values must be unique.")

        scenario_scores = {}
        legacy_scores = {}
        for row, (scenario_id, _scenario_name, contract) in enumerate(
            scenario_rows
        ):
            contract_scores = {}
            for column, result in enumerate(normalized_stasis):
                item = self.matrix.item(row, column)
                try:
                    contract_scores[result] = (
                        int(item.text().strip()) if item else 0
                    )
                except ValueError as error:
                    raise ValueError(
                        f"Score for {contract} / {result} must be a whole number."
                    ) from error
            scenario_scores[scenario_id] = {contract: contract_scores}
            legacy_scores.setdefault(contract, contract_scores)
        return {
            "source_type": "case",
            "case_id": case_id,
            "scenario_ids": scenario_ids,
            "contracts": contracts,
            "results": normalized_stasis,
            "scores": legacy_scores,
            "scenario_scores": scenario_scores,
        }

    def _accept_problem(self):
        try:
            self.problem = self._problem_data()
        except ValueError as error:
            show_message(self, "warning", "Unable to save problem", str(error))
            return
        self.accept()


class TestConstructionView(QWidget):
    """Administrator interface for creating tests and their scoring matrices."""
    close_requested = pyqtSignal()

    def __init__(
        self,
        parent=None,
        language_controller: BilingualTextController | None = None,
    ):
        super().__init__(parent)
        self.repo = Repository()
        self.language_controller = language_controller
        self.admin_id = None
        self.assets = {"cases": [], "scenarios": []}
        self.selected_test_id = None
        self._build_ui()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        header = QHBoxLayout()
        header.addWidget(QLabel("Test construction"))
        header.addStretch()
        self.close_button = QToolButton(self)
        self.close_button.setText("×")
        self.close_button.setToolTip("Close test construction")
        self.close_button.setFixedSize(32, 32)
        self.close_button.setStyleSheet(
            "QToolButton { color: white; background-color: #c0392b; "
            "font-size: 22px; font-weight: bold; border: none; border-radius: 16px; }"
            "QToolButton:hover { background-color: #e74c3c; }"
        )
        self.close_button.clicked.connect(self.close_requested.emit)
        header.addWidget(self.close_button)
        root_layout.addLayout(header)

        layout = QHBoxLayout()
        root_layout.addLayout(layout, 1)
        sidebar = QVBoxLayout()
        sidebar.addWidget(QLabel("Tests"))
        self.test_list = QListWidget()
        self.test_list.currentRowChanged.connect(self._select_test)
        sidebar.addWidget(self.test_list, 1)
        self.new_test_button = QPushButton("New test")
        self.new_test_button.clicked.connect(self.new_test)
        sidebar.addWidget(self.new_test_button)
        self.delete_test_button = QPushButton("Delete test")
        self.delete_test_button.clicked.connect(self.delete_test)
        sidebar.addWidget(self.delete_test_button)
        layout.addLayout(sidebar, 1)

        editor = QVBoxLayout()
        form = QFormLayout()
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Test title")
        form.addRow("Test title:", self.title_input)
        editor.addLayout(form)

        editor.addWidget(QLabel("Problems"))
        self.problem_list = QListWidget()
        self.problem_list.currentRowChanged.connect(self._update_problem_actions)
        editor.addWidget(self.problem_list, 1)
        problem_actions = QHBoxLayout()
        self.add_problem_button = QPushButton("Add problem")
        self.add_problem_button.clicked.connect(self.add_problem)
        problem_actions.addWidget(self.add_problem_button)
        self.edit_problem_button = QPushButton("Edit problem")
        self.edit_problem_button.clicked.connect(self.edit_problem)
        problem_actions.addWidget(self.edit_problem_button)
        self.remove_problem_button = QPushButton("Remove problem")
        self.remove_problem_button.clicked.connect(self.remove_problem)
        problem_actions.addWidget(self.remove_problem_button)
        problem_actions.addStretch()
        self.save_test_button = QPushButton("Save test")
        self.save_test_button.clicked.connect(self.save_test)
        problem_actions.addWidget(self.save_test_button)
        editor.addLayout(problem_actions)
        layout.addLayout(editor, 3)
        self._set_editor_enabled(False)

    def set_admin_id(self, admin_id: int | None):
        self.admin_id = admin_id
        self.assets = (
            self.repo.get_test_assets_by_admin(admin_id)
            if admin_id is not None
            else {"cases": [], "scenarios": []}
        )
        self._reload_tests()
        self._set_editor_enabled(admin_id is not None)

    def _set_editor_enabled(self, enabled):
        self.test_list.setEnabled(enabled)
        self.new_test_button.setEnabled(enabled)
        self.delete_test_button.setEnabled(
            enabled and self.selected_test_id is not None
        )
        self.title_input.setEnabled(enabled)
        self.problem_list.setEnabled(enabled)
        self.add_problem_button.setEnabled(enabled)
        self.save_test_button.setEnabled(enabled)
        self._update_problem_actions()

    def _reload_tests(self, select_test_id=None):
        self.test_list.blockSignals(True)
        self.test_list.clear()
        tests = self.repo.get_tests_by_admin(self.admin_id) if self.admin_id else []
        for test in tests:
            item = QListWidgetItem(test["name"], self.test_list)
            item.setData(Qt.ItemDataRole.UserRole, test)
        self.test_list.blockSignals(False)
        selected_row = next(
            (
                row
                for row in range(self.test_list.count())
                if self.test_list.item(row).data(Qt.ItemDataRole.UserRole)["id"]
                == select_test_id
            ),
            -1,
        )
        if selected_row >= 0:
            self.test_list.setCurrentRow(selected_row)
        else:
            self.new_test()

    def _select_test(self, row):
        if row < 0:
            return
        test = self.test_list.item(row).data(Qt.ItemDataRole.UserRole)
        self.selected_test_id = test["id"]
        self.title_input.setText(test["name"])
        self.problem_list.clear()
        for problem in test["problems"]:
            self._append_problem(problem)
        self.delete_test_button.setEnabled(True)
        self._update_problem_actions()

    def new_test(self):
        self.test_list.clearSelection()
        self.test_list.setCurrentRow(-1)
        self.selected_test_id = None
        self.title_input.clear()
        self.problem_list.clear()
        self.delete_test_button.setEnabled(False)
        self._update_problem_actions()

    def _problem_label(self, problem, index):
        case_name = next(
            (
                case["name"]
                for case in self.assets["cases"]
                if case["id"] == problem.get("case_id")
            ),
            "Unavailable case",
        )
        count = len(problem.get("scenario_ids", []))
        if (
            self.language_controller is not None
            and self.language_controller.language == "zh"
        ):
            return f"题目 {index}：{case_name}（{count} 个候选场景）"
        return f"Problem {index}: {case_name} ({count} candidate scenarios)"

    def _append_problem(self, problem):
        row = self.problem_list.count()
        item = QListWidgetItem(self._problem_label(problem, row + 1))
        item.setData(Qt.ItemDataRole.UserRole, problem)
        self.problem_list.addItem(item)
        self.problem_list.setCurrentItem(item)

    def _open_problem_dialog(self, problem=None):
        if not self.assets["cases"]:
            show_message(
                self,
                "warning",
                "No cases available",
                "Create a case and at least one scenario before adding a problem.",
            )
            return None
        dialog = TestProblemDialog(
            self.assets,
            problem=problem,
            language_controller=self.language_controller,
            parent=self,
        )
        if self.language_controller is not None:
            self.language_controller.install(dialog)
        result = exec_and_delete(dialog)
        if result != QDialog.DialogCode.Accepted:
            return None
        return dialog.problem

    def add_problem(self):
        problem = self._open_problem_dialog()
        if problem is not None:
            self._append_problem(problem)

    def edit_problem(self):
        row = self.problem_list.currentRow()
        if row < 0:
            return
        item = self.problem_list.item(row)
        updated_problem = self._open_problem_dialog(
            item.data(Qt.ItemDataRole.UserRole)
        )
        if updated_problem is None:
            return
        item.setData(Qt.ItemDataRole.UserRole, updated_problem)
        item.setText(self._problem_label(updated_problem, row + 1))

    def remove_problem(self):
        row = self.problem_list.currentRow()
        if row < 0:
            return
        self.problem_list.takeItem(row)
        for index in range(self.problem_list.count()):
            item = self.problem_list.item(index)
            item.setText(
                self._problem_label(
                    item.data(Qt.ItemDataRole.UserRole),
                    index + 1,
                )
            )
        self._update_problem_actions()

    def _update_problem_actions(self, _row=None):
        can_edit = self.problem_list.currentRow() >= 0
        self.edit_problem_button.setEnabled(can_edit)
        self.remove_problem_button.setEnabled(can_edit)

    def save_test(self):
        if self.admin_id is None:
            return
        problems = [
            self.problem_list.item(row).data(Qt.ItemDataRole.UserRole)
            for row in range(self.problem_list.count())
        ]
        try:
            test_id = self.repo.save_test(
                self.admin_id,
                self.title_input.text(),
                problems,
                self.selected_test_id,
            )
        except (LookupError, ValueError, sqlite3.Error) as error:
            show_message(self, "warning", "Unable to save test", str(error))
            return
        self._reload_tests(select_test_id=test_id)
        show_message(
            self,
            "information",
            "Test saved",
            "The test and its problems were saved successfully.",
        )

    def delete_test(self):
        if self.admin_id is None or self.selected_test_id is None:
            return
        answer = show_message(
            self,
            "question",
            "Delete test",
            "Delete this test and all of its problems?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.repo.delete_test(self.admin_id, self.selected_test_id)
        except (LookupError, sqlite3.Error) as error:
            show_message(self, "warning", "Unable to delete test", str(error))
            return
        self._reload_tests()
