import json
import random
import re
import sqlite3
from collections import deque
from pathlib import Path
import sys

try:
    import resource
except ImportError:
    resource = None

from PyQt6.QtCore import QObject, Qt, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from src.database.repository import Repository
from src.core.content_transfer import ContentTransferService
from src.ui.dialogs.admin_registration_dialog import AdminRegistrationDialog
from src.ui.dialogs.board_editor import BoardEditorDialog
from src.ui.dialogs.login_dialog import LoginDialog
from src.ui.dialogs.instructions_dialog import InstructionsDialog
from src.ui.dialogs.monitor_dialog import MonitorDialog
from src.ui.dialogs.test_scenario_dialog import TestScenarioDialog
from src.ui.dialogs.test_report_dialog import TestReportDialog
from src.ui.i18n import (
    BilingualTextController,
    show_message,
    translate_text,
)
from src.ui.views.table_view import TableView
from src.ui.views.test_construction_view import TestConstructionView
from src.ui.views.tree_view import TreeView


class LockdownTerminal(QWidget):
    def __init__(self, submit_command, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        self.output = QPlainTextEdit(self)
        self.output.setReadOnly(True)
        self.output.setStyleSheet(
            "background: #020617; color: #86efac; "
            "font-family: Menlo, monospace;"
        )
        self.input = QLineEdit(self)
        self.input.setPlaceholderText("Enter a lockdown command")
        self.input.returnPressed.connect(self._submit)
        self._submit_command = submit_command
        layout.addWidget(self.output, 1)
        layout.addWidget(self.input)
        self.write("Lockdown mode. Type Help to list available commands.")

    def write(self, text: str):
        self.output.appendPlainText(text)

    def _submit(self):
        command = self.input.text().strip()
        self.input.clear()
        if command:
            self.write(f"> {command}")
            self._submit_command(command)


class StudentIdentityDialog(QDialog):
    def __init__(self, repo: Repository, test_name: str, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.authenticated_student = None
        self.setWindowTitle("Begin test")
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                f"You are about to begin {test_name}. "
                "Enter your student ID and password to verify your student account."
            )
        )
        form = QFormLayout()
        self.student_id = QLineEdit(self)
        self.student_key = QLineEdit(self)
        self.student_key.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Student ID:", self.student_id)
        form.addRow("Password:", self.student_key)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.student_id.setFocus()

    def _accept_if_valid(self):
        try:
            student_id = int(self.student_id.text().strip())
        except ValueError:
            show_message(
                self,
                "warning",
                "Student details required",
                "Enter a numeric student ID.",
            )
            return
        if not self.student_key.text():
            show_message(
                self,
                "warning",
                "Student details required",
                "Enter your password.",
            )
            return
        try:
            self.authenticated_student = self.repo.authenticate_student(
                student_id, self.student_key.text()
            )
        except sqlite3.Error as error:
            show_message(self, "critical", "Student sign-in failed", str(error))
            return
        if self.authenticated_student is None:
            show_message(
                self,
                "warning",
                "Student sign-in failed",
                "The student ID or password is incorrect.",
            )
            return
        self.accept()


class StudentLoginDialog(StudentIdentityDialog):
    def __init__(self, repo: Repository, parent=None):
        super().__init__(repo, "your assigned tests", parent)
        self.setWindowTitle("Student login")


class StudentRegistrationDialog(QDialog):
    def __init__(self, repo: Repository, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.student_id = None
        self.setWindowTitle("Student registration")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_input = QLineEdit(self)
        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Student name:", self.name_input)
        form.addRow("Password:", self.password_input)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self._register)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _register(self):
        if len(self.password_input.text()) < 8:
            show_message(
                self,
                "warning",
                "Student registration failed",
                "Student passwords must contain at least 8 characters.",
            )
            return
        try:
            self.student_id = self.repo.create_student(
                self.name_input.text(),
                self.password_input.text(),
            )
        except (ValueError, sqlite3.Error) as error:
            show_message(
                self,
                "warning",
                "Student registration failed",
                str(error),
            )
            return
        self.accept()


class KeyboardShortcutsDialog(QDialog):
    def __init__(self, language: str = "en", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keyboard shortcuts")
        self.resize(420, 260)
        layout = QVBoxLayout(self)
        shortcuts = QPlainTextEdit(self)
        shortcuts.setReadOnly(True)
        if language == "zh":
            shortcuts.setPlainText(
                "Insert — 添加子资源\n"
                "F2 — 编辑或重命名所选资源\n"
                "Delete — 删除所选资源及其子资源\n"
                "右键单击 — 打开所选资源的上下文菜单"
            )
        else:
            shortcuts.setPlainText(
                "Insert — Add a child asset\n"
                "F2 — Edit or rename the selected asset\n"
                "Delete — Delete the selected asset and its descendants\n"
                "Right-click — Open the selected asset's context menu"
            )
        layout.addWidget(shortcuts)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close,
            parent=self,
        )
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class ProjectDocumentDialog(QDialog):
    def __init__(self, title: str, contents: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(760, 560)
        layout = QVBoxLayout(self)
        document = QPlainTextEdit(self)
        document.setReadOnly(True)
        document.setPlainText(contents)
        layout.addWidget(document)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close,
            parent=self,
        )
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class StudentManagementDialog(QDialog):
    def __init__(self, repo: Repository, admin_id: int, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.admin_id = admin_id
        self.setWindowTitle("Student and test assignments")
        self.resize(760, 560)
        layout = QVBoxLayout(self)

        self.register_button = QPushButton("Create student account", self)
        self.register_button.clicked.connect(self._register_student)
        layout.addWidget(self.register_button)

        assignment_form = QHBoxLayout()
        self.student_combo = QComboBox(self)
        self.test_combo = QComboBox(self)
        self.assign_button = QPushButton("Assign test", self)
        self.assign_button.clicked.connect(self._assign_test)
        assignment_form.addWidget(self.student_combo, 2)
        assignment_form.addWidget(self.test_combo, 2)
        assignment_form.addWidget(self.assign_button)
        layout.addLayout(assignment_form)

        self.assignment_table = QTableWidget(0, 4, self)
        self.assignment_table.setHorizontalHeaderLabels(
            ["Student ID", "Student", "Test", "Status"]
        )
        self.assignment_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.assignment_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.assignment_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.assignment_table, 1)

        footer = QHBoxLayout()
        self.remove_assignment_button = QPushButton("Remove selected assignment")
        self.remove_assignment_button.clicked.connect(self._remove_assignment)
        footer.addWidget(self.remove_assignment_button)
        footer.addStretch()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        footer.addWidget(close_button)
        layout.addLayout(footer)
        self.refresh()

    def refresh(self):
        selected_student_id = self.student_combo.currentData()
        selected_test_id = self.test_combo.currentData()
        self.student_combo.clear()
        for student in self.repo.get_students():
            self.student_combo.addItem(
                f"{student['id']} — {student['name']}",
                student["id"],
            )
        student_index = self.student_combo.findData(selected_student_id)
        if student_index >= 0:
            self.student_combo.setCurrentIndex(student_index)

        self.test_combo.clear()
        for test in self.repo.get_tests_by_admin(self.admin_id):
            self.test_combo.addItem(test["name"], test["id"])
        test_index = self.test_combo.findData(selected_test_id)
        if test_index >= 0:
            self.test_combo.setCurrentIndex(test_index)
        self.assign_button.setEnabled(
            self.student_combo.count() > 0 and self.test_combo.count() > 0
        )

        assignments = self.repo.get_student_test_assignments(self.admin_id)
        self.assignment_table.setRowCount(len(assignments))
        for row, assignment in enumerate(assignments):
            values = (
                str(assignment["student_id"]),
                assignment["student_name"],
                assignment["test_name"],
                "Completed" if assignment["completed_at"] else "Available",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(
                    Qt.ItemDataRole.UserRole,
                    (assignment["student_id"], assignment["test_id"]),
                )
                self.assignment_table.setItem(row, column, item)

    def _register_student(self):
        dialog = StudentRegistrationDialog(self.repo, self)
        owner = self.parentWidget()
        if owner is not None and hasattr(owner, "_prepare_dialog"):
            dialog = owner._prepare_dialog(dialog)
        if not dialog.exec():
            return
        show_message(
            self,
            "information",
            "Student registered",
            f"Student ID: {dialog.student_id}",
        )
        self.refresh()

    def _assign_test(self):
        student_id = self.student_combo.currentData()
        test_id = self.test_combo.currentData()
        if student_id is None or test_id is None:
            return
        try:
            self.repo.assign_test_to_student(
                self.admin_id,
                student_id,
                test_id,
            )
        except (LookupError, ValueError, sqlite3.Error) as error:
            show_message(self, "warning", "Unable to assign test", str(error))
            return
        self.refresh()

    def _remove_assignment(self):
        row = self.assignment_table.currentRow()
        if row < 0:
            return
        assignment = self.assignment_table.item(row, 0).data(
            Qt.ItemDataRole.UserRole
        )
        try:
            self.repo.remove_test_assignment(
                self.admin_id,
                assignment[0],
                assignment[1],
            )
        except (LookupError, ValueError, sqlite3.Error) as error:
            show_message(
                self,
                "warning",
                "Unable to remove assignment",
                str(error),
            )
            return
        self.refresh()


class TestResultsDialog(QDialog):
    def __init__(self, repo: Repository, admin_id: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Test results")
        self.resize(760, 460)
        layout = QVBoxLayout(self)
        self.results_table = QTableWidget(0, 5, self)
        self.results_table.setHorizontalHeaderLabels(
            ["Student ID", "Student", "Test", "Score", "Submitted"]
        )
        self.results_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.results_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.results_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        results = repo.get_test_results_by_admin(admin_id)
        self.results_table.setRowCount(len(results))
        for row, result in enumerate(results):
            values = (
                str(result["student_id"] or ""),
                result["student_name"],
                result["test_name"],
                str(result["score"]),
                result["submitted_at"] or "",
            )
            for column, value in enumerate(values):
                self.results_table.setItem(row, column, QTableWidgetItem(value))
        layout.addWidget(self.results_table, 1)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)


class MainWindow(QMainWindow):
    """Main application window with administrator asset management."""

    def __init__(self):
        super().__init__()
        self.language_controller = BilingualTextController()
        self.setWindowTitle("Bridge Demonstration Tool")
        self.language = "en"
        self.current_mode = "NORMAL"
        self.active_admin_id = None
        self.active_admin_name = None
        self.active_case_id = None
        self.runtime_errors = deque(maxlen=10)
        self.lockdown_active = False
        self.lockdown_student_session = False
        self.lockdown_test = None
        self.lockdown_student_id = None
        self.lockdown_student_name = None
        self.lockdown_scenarios = []
        self.lockdown_scenario_index = 0
        self.lockdown_results = []
        self.lockdown_score = 0
        self.lockdown_current_problem = None
        self.lockdown_play_timer = QTimer(self)
        self.lockdown_play_timer.setInterval(500)
        self.lockdown_play_timer.timeout.connect(self._advance_lockdown_target)
        self.init_ui()
        self.setMinimumSize(1280, 800)
        self.resize(1600, 1000)
        self.statusBar()
        self.language_controller.install(self)
        self._apply_app_theme()
        self._update_admin_indicator()

    def _apply_app_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0b1120;
            }
            QDialog, QMessageBox {
                background-color: #0f172a;
            }
            QWidget {
                color: #e2e8f0;
                font-family: "Aptos", "Arial", sans-serif;
                font-size: 15px;
            }
            QToolBar {
                background-color: #111827;
                border: none;
                border-bottom: 1px solid #263449;
                spacing: 8px;
                padding: 6px;
            }
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 7px 12px;
                color: #e2e8f0;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #38bdf8;
            }
            QPushButton:pressed {
                background-color: #0f172a;
            }
            QPushButton:disabled {
                background-color: #172033;
                border-color: #253247;
                color: #64748b;
            }
            QCheckBox {
                spacing: 10px;
                min-height: 30px;
                padding: 4px 2px;
            }
            QCheckBox::indicator,
            QTreeView::indicator,
            QListView::indicator,
            QTableView::indicator {
                width: 20px;
                height: 20px;
            }
            QCheckBox::indicator:hover,
            QTreeView::indicator:hover,
            QListView::indicator:hover,
            QTableView::indicator:hover {
                border: 1px solid #38bdf8;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 7px 8px;
                min-height: 30px;
            }
            QLineEdit, QTreeWidget, QTableWidget {
                background-color: #111827;
                border: 1px solid #334155;
                border-radius: 6px;
                selection-background-color: #0e7490;
                selection-color: #f8fafc;
            }
            QLineEdit {
                padding: 7px 9px;
            }
            QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit {
                background-color: #111827;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 8px;
                selection-background-color: #0e7490;
                selection-color: #f8fafc;
            }
            QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover,
            QTextEdit:hover, QPlainTextEdit:hover {
                border-color: #38bdf8;
            }
            QComboBox QAbstractItemView {
                background-color: #111827;
                border: 1px solid #334155;
                selection-background-color: #0e7490;
            }
            QTreeWidget::item {
                padding: 5px 4px;
                border-radius: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #164e63;
                color: #f8fafc;
            }
            QGroupBox {
                border: 1px solid #334155;
                border-radius: 8px;
                margin-top: 12px;
                padding: 10px 8px 8px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #7dd3fc;
            }
            QMenu {
                background-color: #111827;
                border: 1px solid #334155;
                padding: 4px;
            }
            QMenu::item {
                padding: 7px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #164e63;
            }
            QToolTip {
                background-color: #1e293b;
                border: 1px solid #475569;
                color: #f8fafc;
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #1e293b;
                border: none;
                border-bottom: 1px solid #334155;
                padding: 6px;
                color: #cbd5e1;
                font-weight: bold;
            }
            QSplitter::handle {
                background-color: #263449;
                width: 2px;
            }
            QStatusBar {
                background-color: #111827;
                border-top: 1px solid #263449;
            }
            QScrollBar:vertical {
                background: #111827;
                width: 10px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: #475569;
                border-radius: 4px;
                min-height: 24px;
            }
        """)

    def init_ui(self):
        self.create_upper_toolbar()
        main_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.main_splitter = main_splitter

        self.left_widget = QWidget()
        left_layout = QVBoxLayout(self.left_widget)
        left_layout.setContentsMargins(5, 5, 5, 5)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search folders, cases, boards, scenarios")
        left_layout.addWidget(self.search_box)

        asset_actions = QHBoxLayout()
        self.btn_add_asset = QPushButton("Add")
        self.btn_add_asset.setToolTip("Add a child asset (Insert key or right-click menu).")
        self.btn_add_asset.clicked.connect(self.add_asset)
        asset_actions.addWidget(self.btn_add_asset)
        self.btn_edit_asset = QPushButton("Edit")
        self.btn_edit_asset.setToolTip("Edit or rename the selected asset (F2).")
        self.btn_edit_asset.clicked.connect(self.edit_asset)
        asset_actions.addWidget(self.btn_edit_asset)
        self.btn_delete_asset = QPushButton("Delete")
        self.btn_delete_asset.setToolTip("Delete the selected asset and its children (Delete).")
        self.btn_delete_asset.clicked.connect(self.delete_asset)
        asset_actions.addWidget(self.btn_delete_asset)
        self.btn_duplicate_asset = QPushButton("Duplicate")
        self.btn_duplicate_asset.clicked.connect(self.duplicate_asset)
        asset_actions.addWidget(self.btn_duplicate_asset)
        self.btn_move_asset = QPushButton("Move")
        self.btn_move_asset.setToolTip(
            "Choose a new parent and review the move before confirming."
        )
        self.btn_move_asset.clicked.connect(self.move_asset)
        asset_actions.addWidget(self.btn_move_asset)
        left_layout.addLayout(asset_actions)

        self.tree_view = TreeView()
        self.tree_view.setToolTip(
            "Right-click for asset actions. Keyboard shortcuts: Insert, F2, Delete."
        )
        self.tree_view.node_selected.connect(self.on_asset_selected)
        self.tree_view.node_double_clicked.connect(self.on_asset_double_clicked)
        self.tree_view.itemChanged.connect(self.on_asset_renamed)
        self.tree_view.itemSelectionChanged.connect(self._update_asset_actions)
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self._show_asset_menu)
        self.search_box.textChanged.connect(self.tree_view.filter_items)
        left_layout.addWidget(self.tree_view)
        self._install_tree_shortcuts()
        self.left_stack = QStackedWidget()
        self.left_stack.addWidget(self.left_widget)
        self.lockdown_terminal = LockdownTerminal(self.execute_lockdown_command)
        self.left_stack.addWidget(self.lockdown_terminal)
        main_splitter.addWidget(self.left_stack)

        self.table_view = TableView(language_controller=self.language_controller)
        self.table_view.mode_changed.connect(self.set_mode)
        self.table_view.scenario_completed.connect(
            self._on_lockdown_scenario_completed
        )
        self.content_stack = QStackedWidget()
        self.content_stack.addWidget(self.table_view)
        self.test_construction_view = TestConstructionView(
            self.content_stack,
            language_controller=self.language_controller,
        )
        self.test_construction_view.close_requested.connect(
            lambda: self.set_mode("NORMAL")
        )
        self.content_stack.addWidget(self.test_construction_view)
        main_splitter.addWidget(self.content_stack)
        main_splitter.setHandleWidth(8)
        main_splitter.setChildrenCollapsible(False)
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)
        self.left_widget.setMinimumWidth(280)
        self.content_stack.setMinimumWidth(600)
        main_splitter.setSizes([380, 1220])
        self.setCentralWidget(main_splitter)

        self.repo = self.tree_view.repo
        self._update_asset_actions()

    def create_upper_toolbar(self):
        self.toolbar = QToolBar("Control Toolbar")
        self.toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        self.btn_test_mode = QPushButton("Test construction")
        self.btn_test_mode.setStyleSheet(
            "background-color: #d35400; font-weight: bold;"
        )
        self.btn_test_mode.clicked.connect(self.toggle_test_mode)
        self.toolbar.addWidget(self.btn_test_mode)
        self.toolbar.addSeparator()

        self.btn_login = QPushButton("Administrator login")
        self.btn_login.clicked.connect(self.on_login_clicked)
        self.toolbar.addWidget(self.btn_login)

        self.btn_register = QPushButton("Administrator registration")
        self.btn_register.clicked.connect(self.on_register_clicked)
        self.toolbar.addWidget(self.btn_register)

        self.btn_logout = QPushButton("Logout")
        self.btn_logout.clicked.connect(self.on_logout_clicked)
        self.btn_logout.setEnabled(False)
        self.toolbar.addWidget(self.btn_logout)

        self.btn_monitor = QPushButton("Monitor")
        self.btn_monitor.setEnabled(False)
        self.btn_monitor.clicked.connect(self.open_monitor)
        self.toolbar.addWidget(self.btn_monitor)

        self.btn_instructions = QPushButton("Instructions")
        self.btn_instructions.clicked.connect(self.open_instructions)
        self.toolbar.addWidget(self.btn_instructions)

        self.btn_language = QPushButton("中文")
        self.btn_language.setProperty("bilingualExempt", True)
        self.btn_language.setToolTip("Switch between Chinese and English.")
        self.btn_language.clicked.connect(self.choose_language)
        self.toolbar.addWidget(self.btn_language)

        self.admin_indicator = QLabel("Administrator: Not signed in")
        self.admin_indicator.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.admin_indicator.setMinimumWidth(190)
        self.admin_indicator.setStyleSheet(
            "background-color: #242831; border: 1px solid #404756; "
            "border-radius: 4px; padding: 4px 10px; "
            "color: #a7f3d0; font-weight: bold;"
        )
        toolbar_spacer = QWidget()
        toolbar_spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        self.toolbar.addWidget(toolbar_spacer)
        self.toolbar.addSeparator()
        self.toolbar.addWidget(self.admin_indicator)
        self.toolbar.hide()
        self._create_cascade_menus()
        self.menuBar().show()

    def _create_cascade_menus(self):
        bar = self.menuBar()
        bar.setNativeMenuBar(False)
        bar.setMinimumHeight(40)
        bar.setAutoFillBackground(True)
        bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        bar.setStyleSheet(
            "QMenuBar { background-color: #111827; color: #f1f5f9; "
            "min-height: 40px; border-bottom: 1px solid #334155; "
            "font-size: 14px; font-weight: 600; }"
            "QMenuBar::item { background-color: transparent; "
            "padding: 7px 14px; margin: 2px 3px; border-radius: 4px; }"
            "QMenuBar::item:selected { background-color: #334155; }"
        )
        self.administration_menu = bar.addMenu("Administrator")
        self.action_admin_register = self.administration_menu.addAction(
            "Administration Registration", self.on_register_clicked
        )
        self.action_admin_login = self.administration_menu.addAction(
            "Administration Login", self.on_login_clicked
        )
        self.action_admin_logout = self.administration_menu.addAction(
            "Administration Logout", self.on_logout_clicked
        )
        self.action_student_login = self.administration_menu.addAction(
            "Student login", self.student_login
        )
        self.administration_menu.addSeparator()
        self.action_export_admin_data = self.administration_menu.addAction(
            "Export administrator data",
            self.export_admin_data,
        )
        self.action_import_admin_data = self.administration_menu.addAction(
            "Import administrator data",
            self.import_admin_data,
        )
        self.administration_menu.addSeparator()
        self.action_lockdown = self.administration_menu.addAction(
            "Administration Lockdown", self.enter_lockdown
        )

        self.tool_menu = bar.addMenu("Tool")
        self.action_monitor = self.tool_menu.addAction("Monitor", self.open_monitor)
        self.tool_menu.addAction("Instruction", self.open_instructions)
        self.tool_menu.addAction("Language", self.choose_language)
        self.tool_menu.addAction(
            "Keyboard shortcuts", self.show_keyboard_shortcuts
        )

        self.test_menu = bar.addMenu("Test")
        self.action_test_construction = self.test_menu.addAction(
            "Test construction", self.toggle_test_mode
        )
        self.action_run_test = self.test_menu.addAction(
            "Run Test", self.run_test_from_menu
        )
        self.action_examine_results = self.test_menu.addAction(
            "Examine test results", self.examine_test_results
        )
        self.action_generate_test_report = self.test_menu.addAction(
            "Generate test report", self.generate_test_report
        )
        self.action_student_management = self.test_menu.addAction(
            "Student management", self.open_student_management
        )

        self.explorer_menu = bar.addMenu("Explorer")
        self.action_readme = self.explorer_menu.addAction(
            "README.md",
            lambda: self.show_project_document("README.md"),
        )
        self.action_requirements = self.explorer_menu.addAction(
            "requirements.txt",
            lambda: self.show_project_document("requirements.txt"),
        )

    def _install_tree_shortcuts(self):
        self.shortcut_add_asset = QShortcut(QKeySequence("Insert"), self.tree_view)
        self.shortcut_add_asset.activated.connect(self.add_asset)
        self.shortcut_edit_asset = QShortcut(QKeySequence("F2"), self.tree_view)
        self.shortcut_edit_asset.activated.connect(self.edit_asset)
        self.shortcut_delete_asset = QShortcut(QKeySequence("Delete"), self.tree_view)
        self.shortcut_delete_asset.activated.connect(self.delete_asset)

    def toggle_language(self):
        self.choose_language()

    def choose_language(self):
        labels = ["English", "中文"]
        current_index = 0 if self.language == "en" else 1
        choice, accepted = QInputDialog.getItem(
            self,
            translate_text("Language", self.language),
            translate_text("Choose interface language:", self.language),
            labels,
            current_index,
            False,
        )
        if accepted:
            self.set_language("en" if choice == "English" else "zh")

    def set_language(self, language: str):
        if language not in {"en", "zh"}:
            raise ValueError(f"Unsupported language: {language}")
        self.language = language
        self.language_controller.set_language(language)
        self.language_controller.install(self)
        self.tree_view.set_language(language)
        self.btn_language.setText("中文" if language == "en" else "English")
        self.btn_language.setToolTip(
            translate_text("Switch between Chinese and English.", language)
        )
        self.table_view.btn_dds_display.setToolTip(
            translate_text(
                "Toggle between side-to-play tricks and contract trick margin.",
                language,
            )
        )

    def show_keyboard_shortcuts(self):
        dialog = self._prepare_dialog(
            KeyboardShortcutsDialog(self.language, self)
        )
        dialog.exec()

    def show_project_document(self, filename: str):
        allowed_files = {"README.md", "requirements.txt"}
        if filename not in allowed_files:
            raise ValueError(f"Unsupported project document: {filename}")
        document_filename = filename
        if filename == "README.md" and self.language == "zh":
            document_filename = "README_zh.md"
        path = Path(__file__).resolve().parents[2] / document_filename
        try:
            contents = path.read_text(encoding="utf-8")
        except OSError as error:
            show_message(
                self,
                "critical",
                "Unable to open project document",
                f"Could not read {filename}: {error}",
            )
            return
        dialog = self._prepare_dialog(
            ProjectDocumentDialog(
                translate_text(filename, self.language),
                contents,
                self,
            )
        )
        dialog.exec()

    def export_admin_data(self):
        if self.active_admin_id is None:
            return
        filename, _selected_filter = QFileDialog.getSaveFileName(
            self,
            translate_text("Save transfer package", self.language),
            "bridge-workspace.bdtpack",
            translate_text("Bridge data package (*.bdtpack)", self.language),
        )
        if not filename:
            return
        if not filename.lower().endswith(".bdtpack"):
            filename = f"{filename}.bdtpack"

        passphrase, accepted = QInputDialog.getText(
            self,
            translate_text("Export passphrase", self.language),
            translate_text(
                "Enter a strong export passphrase (at least 12 characters):",
                self.language,
            ),
            QLineEdit.EchoMode.Password,
        )
        if not accepted:
            return
        confirmation, accepted = QInputDialog.getText(
            self,
            translate_text("Confirm export passphrase", self.language),
            translate_text("Re-enter the export passphrase:", self.language),
            QLineEdit.EchoMode.Password,
        )
        if not accepted:
            return
        if passphrase != confirmation:
            show_message(
                self,
                "warning",
                "Passphrases do not match",
                "The export passphrases do not match.",
            )
            return

        try:
            ContentTransferService(self.repo.db).export_admin_data(
                self.active_admin_id,
                filename,
                passphrase,
            )
        except (LookupError, OSError, sqlite3.Error, ValueError) as error:
            show_message(
                self,
                "critical",
                "Unable to export administrator data",
                str(error),
            )
            return
        show_message(
            self,
            "information",
            "Transfer package exported",
            f"Administrator data was encrypted and saved to:\n{filename}",
        )

    def import_admin_data(self):
        if self.active_admin_id is None:
            return
        filename, _selected_filter = QFileDialog.getOpenFileName(
            self,
            translate_text("Open transfer package", self.language),
            "",
            translate_text("Bridge data package (*.bdtpack)", self.language),
        )
        if not filename:
            return
        passphrase, accepted = QInputDialog.getText(
            self,
            translate_text("Import passphrase", self.language),
            translate_text(
                "Enter the passphrase for this transfer package:",
                self.language,
            ),
            QLineEdit.EchoMode.Password,
        )
        if not accepted:
            return

        service = ContentTransferService(self.repo.db)
        try:
            payload = service.read_package(filename, passphrase)
        except (OSError, ValueError) as error:
            show_message(
                self,
                "critical",
                "Unable to read transfer package",
                str(error),
            )
            return

        record_count = sum(
            len(rows)
            for rows in payload["tables"].values()
        )
        show_message(
            self,
            "information",
            "Transfer package verified",
            f"Package from administrator "
            f"{payload['source_administrator']} contains {record_count} records.",
        )
        answer = show_message(
            self,
            "question",
            "Import administrator data",
            "Import this package into the signed-in administrator account? "
            "Existing data will not be overwritten.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            service.import_admin_data(self.active_admin_id, payload)
        except (LookupError, OSError, sqlite3.Error, ValueError) as error:
            show_message(
                self,
                "critical",
                "Unable to import administrator data",
                str(error),
            )
            return
        self._refresh_assets()
        show_message(
            self,
            "information",
            "Administrator data imported",
            f"The data was added to {self.active_admin_name}.",
        )

    def register_student(self):
        if self.active_admin_id is None:
            self.statusBar().showMessage(
                "Sign in as an administrator to register students.",
                5000,
            )
            return
        dialog = self._prepare_dialog(StudentRegistrationDialog(self.repo, self))
        if dialog.exec():
            show_message(
                self,
                "information",
                "Student registered",
                f"Student account created. Student ID: {dialog.student_id}",
            )

    def open_student_management(self):
        if self.active_admin_id is None:
            self.statusBar().showMessage(
                "Sign in as an administrator to manage students and assignments.",
                5000,
            )
            return
        try:
            dialog = self._prepare_dialog(
                StudentManagementDialog(self.repo, self.active_admin_id, self)
            )
            dialog.exec()
        except sqlite3.Error as error:
            self._show_asset_error(error)

    def student_login(self):
        if self.lockdown_active:
            return
        dialog = self._prepare_dialog(StudentLoginDialog(self.repo, self))
        if not dialog.exec():
            return
        student = dialog.authenticated_student
        self.lockdown_student_id = student["id"]
        self.lockdown_student_name = student["name"]
        self.lockdown_student_session = True
        if not self._activate_lockdown(
            f"Student {student['name']} signed in. Loading assigned tests."
        ):
            self.lockdown_student_id = None
            self.lockdown_student_name = None
            self.lockdown_student_session = False
            return
        self._write_available_student_tests()

    def _write_available_student_tests(self):
        if self.lockdown_student_id is None:
            return
        try:
            tests = self.repo.get_available_tests_for_student(
                self.lockdown_student_id
            )
        except sqlite3.Error as error:
            self.lockdown_terminal.write(f"Unable to load assigned tests: {error}")
            return
        if not tests:
            self.lockdown_terminal.write(
                "No assigned tests are currently available. "
                "Contact your administrator."
            )
            return
        self.lockdown_terminal.write(
            "Available tests (enter Run {TestName} to begin):"
        )
        for test in tests:
            self.lockdown_terminal.write(f"  {test['name']}")

    def examine_test_results(self):
        if self.active_admin_id is None:
            self.statusBar().showMessage(
                "Sign in as an administrator to examine test results.",
                5000,
            )
            return
        try:
            dialog = self._prepare_dialog(
                TestResultsDialog(self.repo, self.active_admin_id, self)
            )
            dialog.exec()
        except sqlite3.Error as error:
            self._show_asset_error(error)

    def generate_test_report(self):
        if self.active_admin_id is None:
            self.statusBar().showMessage(
                "Sign in as an administrator to generate a test report.",
                5000,
            )
            return
        try:
            dialog = self._prepare_dialog(
                TestReportDialog(
                    self.repo,
                    self.active_admin_id,
                    self.language,
                    self,
                )
            )
            dialog.exec()
        except (LookupError, ValueError, sqlite3.Error) as error:
            show_message(
                self,
                "critical",
                "Unable to generate test report",
                str(error),
            )

    def _prepare_dialog(self, dialog):
        if isinstance(dialog, QObject):
            self.language_controller.install(dialog)
        return dialog

    def set_mode(self, mode: str):
        scenario = self.table_view.scenario
        if mode == "TEST":
            if self.active_admin_id is None:
                self.statusBar().showMessage(
                    "Sign in as an administrator before constructing tests.",
                    5000,
                )
                return
            try:
                self._save_active_scenario()
            except (LookupError, sqlite3.Error, ValueError) as error:
                self._show_asset_error(error)
                return
        if mode == "DEMONSTRATION" and (
            not scenario
            or not self.table_view.is_scenario_ready()
            or scenario.contract.upper() == "PASSED_OUT"
        ):
            self.statusBar().showMessage(
                "Complete the scenario auction and contract before demonstration.",
                5000,
            )
            return
        self.current_mode = mode
        is_test_mode = mode == "TEST"
        self.content_stack.setCurrentWidget(
            self.test_construction_view if is_test_mode else self.table_view
        )
        if is_test_mode:
            self.test_construction_view.set_admin_id(self.active_admin_id)
        self.search_box.setEnabled(not is_test_mode)
        self.tree_view.setEnabled(not is_test_mode)
        self.btn_add_asset.setEnabled(not is_test_mode and self.active_admin_id is not None)
        self.btn_edit_asset.setEnabled(
            not is_test_mode and self._selected_asset() is not None
        )
        self.btn_delete_asset.setEnabled(
            not is_test_mode and self._selected_asset() is not None
        )
        self.btn_duplicate_asset.setEnabled(
            not is_test_mode
            and self.active_admin_id is not None
            and self._selected_asset() is not None
        )
        self.btn_login.setEnabled(not is_test_mode)
        self.btn_register.setEnabled(not is_test_mode)
        self.btn_logout.setEnabled(self.active_admin_id is not None)
        self.table_view.set_mode(mode)
        mode_labels = {
            "NORMAL": "Normal mode",
            "DEMONSTRATION": "Demonstration mode",
            "TEST": "Test construction",
        }
        self.statusBar().showMessage(f"{mode_labels.get(mode, mode)} selected", 4000)
        self._update_asset_actions()

    def toggle_test_mode(self):
        self.set_mode("NORMAL" if self.current_mode == "TEST" else "TEST")

    def on_login_clicked(self):
        dialog = self._prepare_dialog(LoginDialog(self))
        if dialog.exec() and dialog.authenticated_admin:
            admin = dialog.authenticated_admin
            self._activate_admin(admin.id, admin.name)
            self.statusBar().showMessage(
                f"Signed in as {admin.name}",
                4000,
            )

    def on_register_clicked(self):
        dialog = self._prepare_dialog(AdminRegistrationDialog(self))
        if dialog.exec():
            admin = self.repo.get_admin_by_id(dialog.admin_id)
            self._activate_admin(
                dialog.admin_id,
                admin.name if admin else None,
                default_case_id=dialog.default_case_id,
            )
            self.statusBar().showMessage(
                "Administrator registered and signed in",
                5000,
            )

    def on_logout_clicked(self):
        if self.active_admin_id is None:
            return
        try:
            self._save_active_scenario()
        except (LookupError, sqlite3.Error, ValueError) as error:
            self._show_asset_error(error)
            return
        self.active_admin_id = None
        self.active_admin_name = None
        self.active_case_id = None
        self.current_mode = "NORMAL"
        self.test_construction_view.set_admin_id(None)
        self.tree_view.load_tree_data(admin_id=None)
        self.table_view.clear_board()
        self.table_view.set_mode("NORMAL")
        self._update_admin_indicator()
        self._update_asset_actions()
        self.set_mode("NORMAL")
        self.statusBar().showMessage("Administrator signed out", 4000)

    def _activate_admin(self, admin_id: int, name=None, default_case_id=None):
        self.active_admin_id = admin_id
        self.active_admin_name = name
        if self.active_admin_name is None:
            admin = self.repo.get_admin_by_id(admin_id)
            self.active_admin_name = admin.name if admin else f"#{admin_id}"
        self.active_case_id = default_case_id or self._first_case_id(admin_id)
        self.tree_view.load_tree_data(admin_id=admin_id)
        self._update_admin_indicator()
        self._update_asset_actions()

    def _update_admin_indicator(self):
        name = self.active_admin_name or "Not signed in"
        self.admin_indicator.setText(f"Administrator: {name}")
        self.admin_indicator.setToolTip(
            f"Current administrator: {name}"
        )
        if self.admin_indicator.parent() is not self.statusBar():
            self.statusBar().addPermanentWidget(self.admin_indicator)
        self.admin_indicator.show()
        self.btn_monitor.setEnabled(self.active_admin_id is not None)
        self.action_admin_logout.setEnabled(self.active_admin_id is not None)
        self.action_student_management.setEnabled(
            self.active_admin_id is not None
        )
        self.action_student_login.setEnabled(not self.lockdown_active)
        self.action_lockdown.setEnabled(self.active_admin_id is not None)
        self.action_export_admin_data.setEnabled(
            self.active_admin_id is not None
        )
        self.action_import_admin_data.setEnabled(
            self.active_admin_id is not None and self.current_mode != "TEST"
        )
        self.action_monitor.setEnabled(self.active_admin_id is not None)
        self.action_run_test.setEnabled(self.active_admin_id is not None)
        self.action_examine_results.setEnabled(
            self.active_admin_id is not None
        )

    def _first_case_id(self, admin_id: int):
        for folder in self.repo.get_folders_by_admin(admin_id):
            cases = self.repo.get_cases_by_folder(folder.id)
            if cases:
                return cases[0].id
        return None

    def _selected_asset(self):
        item = self.tree_view.currentItem()
        if item is None:
            return None
        data = item.data(0, Qt.ItemDataRole.UserRole)
        return data if data else None

    def _update_asset_actions(self):
        selected = self._selected_asset()
        signed_in = self.active_admin_id is not None
        enabled = self.current_mode != "TEST"
        self.btn_logout.setEnabled(signed_in)
        self.btn_add_asset.setEnabled(enabled and signed_in)
        self.btn_edit_asset.setEnabled(enabled and signed_in and selected is not None)
        self.btn_delete_asset.setEnabled(enabled and signed_in and selected is not None)
        self.btn_duplicate_asset.setEnabled(
            enabled and signed_in and selected is not None
        )
        self.btn_move_asset.setEnabled(
            enabled and signed_in and selected is not None
        )
        self.action_test_construction.setEnabled(signed_in)
        self.action_export_admin_data.setEnabled(
            signed_in and self.current_mode != "TEST"
        )
        self.action_import_admin_data.setEnabled(
            signed_in and self.current_mode != "TEST"
        )

    def _show_asset_menu(self, position):
        item = self.tree_view.itemAt(position)
        if item is None:
            return
        self.tree_view.setCurrentItem(item)
        menu = QMenu(self.tree_view)
        menu.addAction("Add child", self.add_asset)
        menu.addAction("Edit", self.edit_asset)
        menu.addAction("Delete", self.delete_asset)
        menu.addAction("Duplicate", self.duplicate_asset)
        menu.addAction("Move", self.move_asset)
        self.language_controller.install(menu)
        menu.exec(self.tree_view.viewport().mapToGlobal(position))

    def duplicate_asset(self):
        selected = self._selected_asset()
        if self.active_admin_id is None or selected is None:
            return
        node_type, node_id = selected
        try:
            duplicate_id = self.repo.duplicate_asset(
                self.active_admin_id, node_type, node_id
            )
            self._refresh_assets(select_asset=(node_type, duplicate_id))
            self.statusBar().showMessage(
                f"{node_type.title()} duplicated", 4000
            )
        except (LookupError, ValueError, sqlite3.Error) as error:
            self._show_asset_error(error)

    def _asset_move_destinations(self, node_type: str, node_id: int):
        folders = self.repo.get_folders_by_admin(self.active_admin_id)
        folders_by_id = {folder.id: folder for folder in folders}

        def folder_path(folder_id):
            parts = []
            seen = set()
            folder = folders_by_id.get(folder_id)
            while folder is not None and folder.id not in seen:
                seen.add(folder.id)
                parts.append(folder.name)
                folder = folders_by_id.get(folder.parent_folder_id)
            return " / ".join(reversed(parts))

        def destination(path, parent_id):
            suffix = f" (#{parent_id})" if parent_id is not None else ""
            return (f"{path}{suffix}", parent_id, path)

        if node_type == "folder":
            source = folders_by_id.get(node_id)
            if source is None:
                raise LookupError(f"Folder {node_id} was not found.")
            children = {}
            for folder in folders:
                children.setdefault(folder.parent_folder_id, []).append(folder.id)
            descendants = {node_id}
            pending = [node_id]
            while pending:
                current = pending.pop()
                for child_id in children.get(current, []):
                    if child_id not in descendants:
                        descendants.add(child_id)
                        pending.append(child_id)

            destinations = []
            if source.parent_folder_id is not None:
                destinations.append(
                    destination(
                        translate_text("Root level", self.language),
                        None,
                    )
                )
            for folder in folders:
                if (
                    folder.id not in descendants
                    and folder.id != source.parent_folder_id
                ):
                    destinations.append(
                        destination(
                            folder_path(folder.id),
                            folder.id,
                        )
                    )
            return destinations

        cases = []
        for folder in folders:
            cases.extend(
                (folder, case)
                for case in self.repo.get_cases_by_folder(folder.id)
            )
        cases_by_id = {case.id: (folder, case) for folder, case in cases}

        if node_type == "case":
            source = self.repo.get_case_by_id(node_id)
            if source is None or source.folder_id not in folders_by_id:
                raise LookupError(f"Case {node_id} was not found.")
            return [
                destination(folder_path(folder.id), folder.id)
                for folder in folders
                if folder.id != source.folder_id
            ]

        boards = []
        for folder, case in cases:
            boards.extend(
                (folder, case, board)
                for board in self.repo.get_boards_by_case(case.id)
            )
        boards_by_id = {
            board.id: (folder, case, board)
            for folder, case, board in boards
        }

        if node_type == "board":
            source = self.repo.get_board_by_id(node_id)
            if source is None or source.case_id not in cases_by_id:
                raise LookupError(f"Board {node_id} was not found.")
            return [
                destination(
                    f"{folder_path(folder.id)} / {case.name}",
                    case.id,
                )
                for folder, case in cases
                if case.id != source.case_id
            ]

        if node_type == "scenario":
            source = self.repo.get_scenario_by_id(node_id)
            if source is None or source.board_id not in boards_by_id:
                raise LookupError(f"Scenario {node_id} was not found.")
            return [
                destination(
                    f"{folder_path(folder.id)} / {case.name} / "
                    f"{board.description or f'Board #{board.id}'}",
                    board.id,
                )
                for folder, case, board in boards
                if board.id != source.board_id
            ]

        raise ValueError(f"Unsupported asset type: {node_type}")

    @staticmethod
    def _asset_tree_path(item):
        parts = []
        while item is not None:
            parts.append(item.text(0))
            item = item.parent()
        return " / ".join(reversed(parts))

    def move_asset(self):
        selected = self._selected_asset()
        if self.active_admin_id is None or selected is None:
            return
        node_type, node_id = selected
        item = self.tree_view.currentItem()
        if item is None:
            return

        try:
            destinations = self._asset_move_destinations(node_type, node_id)
            if not destinations:
                show_message(
                    self,
                    "warning",
                    "No valid destinations",
                    "There are no other valid destinations for this asset.",
                )
                return

            choice, accepted = self._prompt_asset_choice(
                translate_text("Move asset", self.language),
                translate_text("Choose a destination:", self.language),
                [entry[0] for entry in destinations],
            )
            if not accepted:
                return
            target = next(
                (entry for entry in destinations if entry[0] == choice),
                None,
            )
            if target is None:
                raise ValueError("Choose one of the listed destinations.")

            source_path = self._asset_tree_path(item)
            destination_parent = target[2]
            destination_path = (
                item.text(0)
                if target[1] is None
                else f"{destination_parent} / {item.text(0)}"
            )
            preview = (
                "Review this move before confirming:\n\n"
                f"From: {source_path}\n"
                f"To: {destination_path}\n\n"
                "This moves the selected asset and all descendants. Continue?"
            )
            answer = show_message(
                self,
                "question",
                "Move asset",
                preview,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

            active_scenario = self.table_view.scenario
            active_scenario_id = (
                active_scenario.id if active_scenario is not None else None
            )

            def contains_active_scenario(tree_item):
                if (
                    active_scenario_id is not None
                    and tree_item.data(0, Qt.ItemDataRole.UserRole)
                    == ("scenario", active_scenario_id)
                ):
                    return True
                return any(
                    contains_active_scenario(tree_item.child(index))
                    for index in range(tree_item.childCount())
                )

            reload_active_scenario = contains_active_scenario(item)
            if reload_active_scenario:
                self._save_active_scenario()

            moved = self.repo.move_asset(
                self.active_admin_id,
                node_type,
                node_id,
                target[1],
            )
            if not moved:
                self.statusBar().showMessage(
                    "The asset is already in that location.",
                    5000,
                )
                return

            self._refresh_assets(select_asset=selected)
            if reload_active_scenario and active_scenario_id is not None:
                self._load_scenario(active_scenario_id)
            self.statusBar().showMessage(
                f"{node_type.title()} moved to {destination_path}",
                5000,
            )
        except (LookupError, ValueError, sqlite3.Error) as error:
            self._show_asset_error(error)

    def _create_asset_text_dialog(self, title: str, label: str) -> QInputDialog:
        dialog = QInputDialog(self)
        dialog.setWindowTitle(translate_text(title, self.language))
        dialog.setLabelText(translate_text(label, self.language))
        dialog.setInputMode(QInputDialog.InputMode.TextInput)
        dialog.setFixedWidth(600)
        editor = dialog.findChild(QLineEdit)
        if editor is not None:
            editor.setFixedSize(500, 36)
        return dialog

    def _prompt_asset_name(self, title: str, label: str):
        dialog = self._create_asset_text_dialog(title, label)
        accepted = dialog.exec() == QInputDialog.DialogCode.Accepted
        return dialog.textValue(), accepted

    def _create_asset_choice_dialog(
        self,
        title: str,
        label: str,
        choices: list[str],
    ) -> QInputDialog:
        dialog = QInputDialog(self)
        dialog.setWindowTitle(translate_text(title, self.language))
        dialog.setLabelText(translate_text(label, self.language))
        dialog.setInputMode(QInputDialog.InputMode.TextInput)
        dialog.setComboBoxItems(choices)
        dialog.setComboBoxEditable(False)
        dialog.setFixedWidth(600)
        editor = dialog.findChild(QComboBox)
        if editor is not None:
            editor.setFixedSize(500, 36)
        return dialog

    def _prompt_asset_choice(self, title: str, label: str, choices: list[str]):
        dialog = self._create_asset_choice_dialog(title, label, choices)
        accepted = dialog.exec() == QInputDialog.DialogCode.Accepted
        return dialog.textValue(), accepted

    def add_asset(self):
        if self.active_admin_id is None:
            self.statusBar().showMessage("Sign in or register before adding assets.", 5000)
            return

        selected = self._selected_asset()
        node_type, node_id = selected if selected else (None, None)
        try:
            if node_type is None:
                name, accepted = self._prompt_asset_name(
                    translate_text("New folder", self.language),
                    translate_text("Folder name:", self.language),
                )
                if accepted and name.strip():
                    self.repo.create_folder(
                        self.active_admin_id,
                        None,
                        name.strip(),
                    )
                    self._refresh_assets()
            elif node_type == "folder":
                choices = [
                    translate_text("Create a case", self.language),
                    translate_text("Create a child folder", self.language),
                ]
                choice, accepted = self._prompt_asset_choice(
                    translate_text("Add to folder", self.language),
                    translate_text("Choose what to add:", self.language),
                    choices,
                )
                if not accepted:
                    return
                if choice == choices[0]:
                    self._create_case(node_id)
                elif choice == choices[1]:
                    name, name_accepted = self._prompt_asset_name(
                        translate_text("New child folder", self.language),
                        translate_text("Folder name:", self.language),
                    )
                    if name_accepted and name.strip():
                        self.repo.create_folder(
                            self.active_admin_id,
                            node_id,
                            name.strip(),
                        )
                        self._refresh_assets()
            elif node_type == "case":
                self._create_board(node_id)
            elif node_type == "board":
                self._create_scenario(node_id)
            elif node_type == "scenario":
                scenario = self.repo.get_scenario_by_id(node_id)
                if scenario is None:
                    raise LookupError(f"Scenario {node_id} was not found.")
                self._create_scenario(scenario.board_id)
        except (LookupError, ValueError, sqlite3.Error) as error:
            self._show_asset_error(error)

    def _create_case(self, folder_id: int):
        name, accepted = self._prompt_asset_name(
            translate_text("New case", self.language),
            translate_text("Case name:", self.language),
        )
        if accepted and name.strip():
            self.repo.create_case(folder_id, name.strip())
            self._refresh_assets()

    def _create_board(self, case_id: int):
        self._open_board_editor(case_id=case_id)

    def _create_scenario(self, board_id: int):
        self._save_active_scenario()
        scenario_id = self.repo.create_scenario(
            board_id=board_id,
            bidding_route="",
            declarer="SOUTH",
            contract="",
            risk_status="NONE",
            is_targeted=0,
            targeted_sequence="[]",
        )
        self._refresh_assets(select_asset=("scenario", scenario_id))
        self._load_scenario(scenario_id)

    def edit_asset(self):
        selected = self._selected_asset()
        if self.active_admin_id is None or selected is None:
            return
        node_type, node_id = selected
        try:
            if node_type == "board":
                self._open_board_editor(board_id=node_id)
            elif node_type in {"folder", "case", "scenario"}:
                item = self.tree_view.currentItem()
                if item is not None:
                    self.tree_view.editItem(item, 0)
        except (LookupError, ValueError, sqlite3.Error) as error:
            self._show_asset_error(error)

    def on_asset_renamed(self, item, _column):
        asset = item.data(0, Qt.ItemDataRole.UserRole)
        if not asset:
            return
        node_type, node_id = asset
        name = item.text(0).strip()
        if not name:
            self._refresh_assets(select_asset=asset)
            return
        try:
            if node_type == "folder":
                self.repo.rename_folder(node_id, name)
            elif node_type == "case":
                self.repo.rename_case(node_id, name)
            elif node_type == "scenario":
                self.repo.rename_scenario(node_id, name)
                scenario = self.table_view.scenario
                if scenario and scenario.id == node_id:
                    scenario.name = name
        except (LookupError, sqlite3.Error) as error:
            self._show_asset_error(error)
            self._refresh_assets(select_asset=asset)

    def delete_asset(self):
        selected = self._selected_asset()
        if self.active_admin_id is None or selected is None:
            return
        node_type, node_id = selected
        item = self.tree_view.currentItem()
        name = item.text(0) if item else f"{node_type} {node_id}"
        answer = show_message(
            self,
            "question",
            translate_text("Delete asset", self.language),
            translate_text(
                f"Delete {name}?\nChild assets will also be deleted.",
                self.language,
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        clear_loaded_scenario = False
        delete_methods = {
            "folder": self.repo.delete_folder,
            "case": self.repo.delete_case,
            "board": self.repo.delete_board,
            "scenario": self.repo.delete_scenario,
        }
        delete_method = delete_methods.get(node_type)
        if delete_method is None:
            self.statusBar().showMessage(
                f"Deleting {node_type} assets is not supported.",
                5000,
            )
            return
        try:
            scenario = self.table_view.scenario
            if scenario is not None:
                board = self.repo.get_board_by_id(scenario.board_id)
                case = (
                    self.repo.get_case_by_id(board.case_id)
                    if board is not None
                    else None
                )
                clear_loaded_scenario = (
                    (node_type == "scenario" and node_id == scenario.id)
                    or (node_type == "board" and board and node_id == board.id)
                    or (node_type == "case" and case and node_id == case.id)
                    or (
                        node_type == "folder"
                        and case
                        and node_id == case.folder_id
                    )
                )
            delete_method(node_id)
            if clear_loaded_scenario:
                self.table_view.clear_board()
            if node_type == "case" and self.active_case_id == node_id:
                self.active_case_id = None
            self._refresh_assets()
        except (LookupError, sqlite3.Error) as error:
            self._show_asset_error(error)

    def _open_board_editor(self, board_id=None, case_id=None):
        try:
            dialog = self._prepare_dialog(BoardEditorDialog(
                case_id=case_id,
                board_id=board_id,
                parent=self,
            ))
            if dialog.exec():
                self._refresh_assets(
                    select_asset=("board", dialog.saved_board_id)
                )
        except (LookupError, ValueError, sqlite3.Error) as error:
            self._show_asset_error(error)

    def on_asset_selected(self, node_type: str, node_id: int):
        try:
            if node_type == "board":
                board = self.repo.get_board_by_id(node_id)
                if board is None:
                    raise LookupError(f"Board {node_id} was not found.")
                self.active_case_id = board.case_id
            elif node_type == "scenario":
                scenario = self.repo.get_scenario_by_id(node_id)
                if scenario is None:
                    raise LookupError(f"Scenario {node_id} was not found.")
                board = self.repo.get_board_by_id(scenario.board_id)
                if board is None:
                    raise LookupError(f"Board {scenario.board_id} was not found.")
                self.active_case_id = board.case_id
            elif node_type == "case":
                self.active_case_id = node_id
        except (LookupError, ValueError, TypeError, sqlite3.Error) as error:
            self._show_asset_error(error)
        self._update_asset_actions()

    def on_asset_double_clicked(self, node_type: str, node_id: int):
        if node_type != "scenario":
            return
        try:
            self._save_active_scenario()
            self._load_scenario(node_id)
        except (LookupError, ValueError, TypeError, sqlite3.Error) as error:
            self._show_asset_error(error)

    def _load_scenario(self, scenario_id: int):
        scenario = self.repo.get_scenario_by_id(scenario_id)
        if scenario is None:
            raise LookupError(f"Scenario {scenario_id} was not found.")
        board = self.repo.get_board_by_id(scenario.board_id)
        if board is None:
            raise LookupError(f"Board {scenario.board_id} was not found.")
        configuration = self.repo.get_board_configuration(
            board.board_configuration_id
        )
        if configuration is None:
            raise LookupError(
                f"Configuration {board.board_configuration_id} was not found."
            )
        labels = self.repo.get_labels_by_scenario(scenario.id)
        self.active_case_id = board.case_id
        self.table_view.load_board(board, configuration, scenario, labels)
        self.statusBar().showMessage(f"Scenario {scenario_id} loaded", 4000)

    def enter_lockdown(self):
        if self.lockdown_active:
            return True
        if self.active_admin_id is None or not self.active_admin_name:
            self.statusBar().showMessage(
                "Sign in as an administrator before entering lockdown.", 5000
            )
            return False
        password, accepted = QInputDialog.getText(
            self,
            translate_text("Confirm lockdown", self.language),
            translate_text(
                "Re-enter the administrator password:",
                self.language,
            ),
            QLineEdit.EchoMode.Password,
        )
        if not accepted:
            return False
        try:
            admin = self.repo.authenticate_admin(self.active_admin_name, password)
        except sqlite3.Error as error:
            self._show_asset_error(error)
            return False
        if admin is None or admin.id != self.active_admin_id:
            show_message(
                self,
                "warning",
                "Lockdown denied",
                "The password is incorrect.",
            )
            return False
        return self._activate_lockdown(
            f"Administrator {self.active_admin_name} entered lockdown."
        )

    def _activate_lockdown(self, welcome_message: str) -> bool:
        try:
            self._save_active_scenario()
            if self.current_mode != "NORMAL":
                self.set_mode("NORMAL")
        except (LookupError, sqlite3.Error, ValueError) as error:
            self._show_asset_error(error)
            return False

        self.lockdown_active = True
        self.current_mode = "LOCKDOWN"
        self.table_view.clear_board()
        self.left_stack.setCurrentWidget(self.lockdown_terminal)
        self.table_view.set_lockdown_mode(True)
        self.toolbar.hide()
        self.menuBar().hide()
        self.statusBar().hide()
        self.lockdown_terminal.write(welcome_message)
        self.lockdown_terminal.input.setFocus()
        return True

    def _exit_lockdown(self):
        self.lockdown_play_timer.stop()
        self.lockdown_test = None
        self.lockdown_student_id = None
        self.lockdown_student_name = None
        self.lockdown_student_session = False
        self.lockdown_scenarios = []
        self.lockdown_active = False
        self.left_stack.setCurrentWidget(self.left_widget)
        self.toolbar.hide()
        self.menuBar().show()
        self.statusBar().show()
        self.current_mode = "NORMAL"
        self.active_admin_id = None
        self.active_admin_name = None
        self.active_case_id = None
        self.test_construction_view.set_admin_id(None)
        self.tree_view.load_tree_data(admin_id=None)
        self.table_view.clear_board()
        self.table_view.set_lockdown_mode(False)
        self.table_view.set_mode("NORMAL")
        self.lockdown_terminal.output.clear()
        self._update_admin_indicator()
        self._update_asset_actions()
        self.statusBar().showMessage(
            "Lockdown mode ended; all accounts signed out.",
            4000,
        )

    def execute_lockdown_command(self, command: str):
        if not self.lockdown_active:
            return
        if command.casefold() in {"help", "?"}:
            if self.lockdown_student_session:
                self.lockdown_terminal.write(
                    "Commands: Run {AssignedTestName}, Help, Exit"
                )
            else:
                self.lockdown_terminal.write(
                    "Commands: Run ({BoardName}){ScenarioName}, "
                    "Run {TestName}, Help, Exit"
                )
            return
        if command.casefold() == "exit":
            self._exit_lockdown()
            return

        scenario_match = re.fullmatch(
            r"Run\s+\(([^)]+)\)\s*(.+)", command, flags=re.IGNORECASE
        )
        if scenario_match:
            if self.lockdown_student_session:
                self.lockdown_terminal.write(
                    "Students may only run tests assigned to their account."
                )
                return
            board_name, scenario_name = (
                scenario_match.group(1).strip(),
                scenario_match.group(2).strip(),
            )
            try:
                scenario_id = self.repo.get_scenario_id_by_names(
                    self.active_admin_id, board_name, scenario_name
                )
            except sqlite3.Error as error:
                self.lockdown_terminal.write(f"Scenario lookup failed: {error}")
                return
            if scenario_id is None:
                self.lockdown_terminal.write(
                    f"No scenario named {scenario_name!r} was found "
                    f"on board {board_name!r}."
                )
                return
            self._run_lockdown_scenario(scenario_id)
            return

        test_match = re.fullmatch(r"Run\s+(.+)", command, flags=re.IGNORECASE)
        if test_match:
            self.start_lockdown_test(test_match.group(1).strip())
            return
        self.lockdown_terminal.write("Unknown command. Type Help for available commands.")

    def _load_lockdown_scenario(self, scenario_id: int, *, test_mode=False):
        scenario = self.repo.get_scenario_by_id(scenario_id)
        if scenario is None:
            raise LookupError(f"Scenario {scenario_id} was not found.")
        board = self.repo.get_board_by_id(scenario.board_id)
        if board is None:
            raise LookupError(f"Board for scenario {scenario_id} was not found.")
        configuration = self.repo.get_board_configuration(
            board.board_configuration_id
        )
        if configuration is None:
            raise LookupError(f"Board configuration for {board.id} was not found.")
        labels = self.repo.get_labels_by_scenario(scenario_id)
        self.active_case_id = board.case_id
        self.table_view.load_board(
            board,
            configuration,
            scenario,
            labels,
            force_robot=test_mode,
        )
        self.table_view.test_playback_active = test_mode
        self.table_view.current_side = scenario.declarer
        self.table_view.btn_side.setText(f"Human seat: {scenario.declarer}")
        self.table_view.view_mode = "HIDDEN"
        self.table_view.btn_view_mode.setText("View: Hidden")
        self.table_view._apply_view_mode()
        self.table_view.rule_mode = "LABEL" if test_mode else "TARGET"
        self.table_view.btn_rule_mode.setText(
            f"Rule: {self.table_view.rule_mode.title()}"
        )
        if not self.table_view.set_mode("DEMONSTRATION"):
            raise ValueError(f"Scenario {scenario_id} is not ready to play.")
        if test_mode:
            self.table_view._advance_robots()

    def _run_lockdown_scenario(self, scenario_id: int):
        if self.lockdown_test is not None:
            self.lockdown_terminal.write(
                "Finish or exit the current test before running a separate scenario."
            )
            return
        try:
            self._save_active_scenario()
            self._load_lockdown_scenario(scenario_id)
            if not self.table_view.target_sequence:
                raise ValueError("This scenario has no recorded target sequence.")
        except (LookupError, ValueError, sqlite3.Error) as error:
            self.lockdown_terminal.write(f"Cannot run scenario: {error}")
            return
        self.lockdown_terminal.write("Playing the saved target sequence.")
        self.lockdown_play_timer.start()

    def _advance_lockdown_target(self):
        if not self.lockdown_active or self.lockdown_test is not None:
            self.lockdown_play_timer.stop()
            return
        table = self.table_view
        if (
            table.target_index >= len(table.target_sequence)
            or table._is_board_complete()
        ):
            self.lockdown_play_timer.stop()
            if not table._completion_emitted:
                table._completion_emitted = True
                self._on_lockdown_scenario_completed()
            return
        previous_index = table.target_index
        table.play_next_target_card()
        if (
            table.target_index == previous_index
            and not table._completion_emitted
        ):
            self.lockdown_play_timer.stop()
            self.lockdown_terminal.write(
                f"Playback stopped: {table.center_info.text()}"
            )

    def run_test_from_menu(self):
        if self.active_admin_id is None:
            self.statusBar().showMessage(
                "Sign in as an administrator before running a test.", 5000
            )
            return
        if not self.enter_lockdown():
            return
        try:
            tests = self.repo.get_tests_by_admin(self.active_admin_id)
        except sqlite3.Error as error:
            self.lockdown_terminal.write(f"Unable to load tests: {error}")
            return
        if not tests:
            self.lockdown_terminal.write("There are no tests to run.")
            return
        name, accepted = QInputDialog.getItem(
            self,
            translate_text("Run Test", self.language),
            translate_text("Select a test:", self.language),
            [test["name"] for test in tests],
            0,
            False,
        )
        if accepted:
            self.start_lockdown_test(name)

    def start_lockdown_test(self, test_name: str):
        if self.lockdown_test is not None:
            self.lockdown_terminal.write("A test is already in progress.")
            return
        try:
            if self.lockdown_student_session:
                if self.lockdown_student_id is None:
                    self.lockdown_terminal.write("Student session is not valid.")
                    return
                test = self.repo.get_assigned_test_by_name(
                    self.lockdown_student_id,
                    test_name,
                )
            elif self.active_admin_id is not None:
                test = self.repo.get_test_by_name(
                    self.active_admin_id,
                    test_name,
                )
            else:
                self.lockdown_terminal.write(
                    "Sign in as a student or administrator before running a test."
                )
                return
        except (sqlite3.Error, ValueError) as error:
            self.lockdown_terminal.write(f"Unable to load test: {error}")
            return
        if test is None:
            if self.lockdown_student_session:
                self.lockdown_terminal.write(
                    f"Test {test_name!r} is not assigned or is already completed."
                )
            else:
                self.lockdown_terminal.write(f"Test {test_name!r} was not found.")
            return
        scenarios = []
        for problem in test["problems"]:
            candidates = problem.get("scenario_ids", [])
            if candidates:
                scenarios.append(
                    {
                        "scenario_id": random.choice(candidates),
                        "problem": problem,
                    }
                )
        if not scenarios:
            self.lockdown_terminal.write("This test has no scenarios.")
            return
        if not self.lockdown_student_session:
            dialog = self._prepare_dialog(
                StudentIdentityDialog(self.repo, test["name"], self)
            )
            if not dialog.exec():
                return
            student_id = dialog.authenticated_student["id"]
            try:
                available_tests = self.repo.get_available_tests_for_student(
                    student_id
                )
            except sqlite3.Error as error:
                self.lockdown_terminal.write(
                    f"Unable to verify test assignment: {error}"
                )
                return
            if not any(item["id"] == test["id"] for item in available_tests):
                show_message(
                    self,
                    "warning",
                    "Test unavailable",
                    "This test is not assigned to the student or has already "
                    "been completed.",
                )
                return
            self.lockdown_student_id = student_id
            self.lockdown_student_name = dialog.authenticated_student["name"]
        self.lockdown_test = test
        self.lockdown_scenarios = scenarios
        self.lockdown_scenario_index = 0
        self.lockdown_results = []
        self.lockdown_score = 0
        self.lockdown_terminal.write(
            f"Test {test['name']} started for {self.lockdown_student_id}."
        )
        self._start_next_test_scenario()

    def _start_next_test_scenario(self):
        if self.lockdown_scenario_index >= len(self.lockdown_scenarios):
            self._finish_lockdown_test()
            return
        self.lockdown_current_problem = self.lockdown_scenarios[
            self.lockdown_scenario_index
        ]["problem"]
        scenario_id = self.lockdown_scenarios[
            self.lockdown_scenario_index
        ]["scenario_id"]
        try:
            self._save_active_scenario()
            self._load_lockdown_scenario(scenario_id, test_mode=True)
        except (LookupError, ValueError, sqlite3.Error) as error:
            self.lockdown_terminal.write(f"Cannot start scenario: {error}")
            self.lockdown_test = None
            return
        scenario = self.table_view.scenario
        problem = self.lockdown_current_problem or {}
        bidding_route = problem.get("scenario_bidding_routes", {}).get(
            scenario_id
        ) or scenario.bidding_route
        self.lockdown_terminal.write(
            f"Bidding: {bidding_route or 'No bidding information.'}"
        )
        information = problem.get("scenario_information", {}).get(
            scenario_id
        ) or scenario.information
        if information:
            self.lockdown_terminal.write(f"Scenario information: {information}")
        self.lockdown_terminal.write(
            f"Scenario {self.lockdown_scenario_index + 1} of "
            f"{len(self.lockdown_scenarios)} started."
        )

    def _on_lockdown_scenario_completed(self):
        if not self.lockdown_active or self.table_view.game is None:
            return
        self.lockdown_play_timer.stop()
        game = self.table_view.game
        scenario = self.table_view.scenario
        contract = scenario.contract.upper()
        contract_match = re.match(r"^([1-7])", contract)
        tricks_taken = (
            sum(
                game.tricks_won[seat]
                for seat in self.table_view.PARTNERS[game.declarer]
            )
            if game.declarer
            else 0
        )
        stasis = (
            tricks_taken - (int(contract_match.group(1)) + 6)
            if contract_match
            else 0
        )
        result_key = "=" if stasis == 0 else f"{stasis:+d}"
        awarded_score = 0
        problem = self.lockdown_current_problem
        if problem is not None:
            contract_scores = problem.get("scores", {}).get(contract, {})
            if result_key in contract_scores:
                awarded_score = int(contract_scores[result_key])
            self.lockdown_score += awarded_score
            self.lockdown_results.append(
                {
                    "problem_number": self.lockdown_scenario_index + 1,
                    "scenario_id": scenario.id,
                    "contract": contract,
                    "tricks_taken": tricks_taken,
                    "stasis": result_key,
                    "score": awarded_score,
                }
            )
        info = f"\n\n{scenario.information}" if scenario.information else ""
        if problem is not None:
            is_last = self.lockdown_scenario_index + 1 >= len(
                self.lockdown_scenarios
            )
            caption = "Finish test" if is_last else "Proceed to next scenario"
            dialog = TestScenarioDialog(
                "Scenario result",
                "Scenario complete",
                details=(
                    ("Contract", contract),
                    ("Declarer tricks", str(tricks_taken)),
                    ("Stasis", result_key),
                    ("Scenario score", str(awarded_score)),
                ),
                information=scenario.information,
                action_text=caption,
                language=self.language_controller.language,
                parent=self,
            )
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.lockdown_scenario_index += 1
                self._start_next_test_scenario()
        else:
            show_message(
                self,
                "information",
                "Scenario result",
                f"Contract: {contract}\nDeclarer tricks: {tricks_taken}\n"
                f"Stasis: {result_key}{info}",
            )
            self.lockdown_terminal.write("Scenario playback complete.")

    def _finish_lockdown_test(self):
        test = self.lockdown_test
        if test is None:
            return
        try:
            self.repo.save_test_result(
                test["id"],
                self.lockdown_student_id,
                self.lockdown_results,
                self.lockdown_score,
            )
        except (LookupError, sqlite3.Error) as error:
            self.runtime_errors.append(f"Test result save failed: {error}")
            self.lockdown_terminal.write(f"Could not save test result: {error}")
            show_message(
                self,
                "critical",
                "Result could not be saved",
                str(error),
            )
            return
        dialog = TestScenarioDialog(
            "Test complete",
            test["name"],
            details=(
                ("Student ID", str(self.lockdown_student_id)),
                ("Student name", self.lockdown_student_name or ""),
                ("Total score", str(self.lockdown_score)),
            ),
            action_text="Close",
            language=self.language_controller.language,
            parent=self,
        )
        dialog.exec()
        self.lockdown_terminal.write(
            f"Test complete. Score: {self.lockdown_score}."
        )
        self.lockdown_test = None
        self.lockdown_scenarios = []
        self.lockdown_current_problem = None
        if self.lockdown_student_session:
            self._write_available_student_tests()
        else:
            self.lockdown_student_id = None
            self.lockdown_student_name = None

    def _save_active_scenario(self):
        scenario = self.table_view.scenario
        if scenario is None:
            return
        route = " ".join(self.table_view.bidding_route)
        target_sequence = json.dumps(self.table_view.target_sequence)
        self.repo.update_scenario(
            scenario.id,
            route,
            scenario.declarer,
            scenario.contract,
            scenario.risk_status,
            int(bool(scenario.is_targeted)),
            target_sequence,
            scenario.information,
        )
        self.repo.replace_labels(scenario.id, self.table_view.labels)
        scenario.bidding_route = route
        scenario.targeted_sequence = target_sequence

    def _refresh_assets(self, select_asset=None):
        self.tree_view.load_tree_data(admin_id=self.active_admin_id)
        if self.active_case_id and self.repo.get_case_by_id(self.active_case_id) is None:
            self.active_case_id = None
        if self.active_case_id is None:
            self.active_case_id = self._first_case_id(self.active_admin_id)
        if select_asset is not None:
            target_item = self._find_asset_item(select_asset)
            if target_item is not None:
                self.tree_view.setCurrentItem(target_item)
        self._update_asset_actions()

    def _find_asset_item(self, asset_key):
        def find_in(item):
            if item.data(0, Qt.ItemDataRole.UserRole) == asset_key:
                return item
            for child_index in range(item.childCount()):
                found = find_in(item.child(child_index))
                if found is not None:
                    return found
            return None

        for index in range(self.tree_view.topLevelItemCount()):
            found = find_in(self.tree_view.topLevelItem(index))
            if found is not None:
                return found
        return None

    def _show_asset_error(self, error):
        message = f"Asset operation failed: {error}"
        self.runtime_errors.append(message)
        self.statusBar().showMessage(message, 8000)

    def open_monitor(self):
        if self.active_admin_id is None:
            return
        table = self.table_view
        memory_status = (
            f"Peak process memory: {self._peak_process_memory_mb():.1f} MB"
            if resource is not None
            else "Peak process memory: Unavailable"
        )
        runtime_status = (
            f"Undo snapshots: {len(table.move_history)}/64\n"
            f"Target sequence: {table.target_index}/"
            f"{len(table.target_sequence)}\n{memory_status}"
        )
        errors = list(self.runtime_errors)
        if table.robot_error_message:
            errors.append(f"Robot error: {table.robot_error_message}")
        try:
            dialog = self._prepare_dialog(
                MonitorDialog(
                    self.repo,
                    self.active_admin_id,
                    {
                        "runtime": runtime_status,
                        "errors": errors,
                    },
                    self,
                )
            )
            dialog.exec()
        except sqlite3.Error as error:
            self._show_asset_error(error)
            show_message(
                self,
                "critical",
                "Monitor unavailable",
                f"Unable to read monitoring statistics: {error}",
            )

    @staticmethod
    def _peak_process_memory_mb():
        peak_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if sys.platform == "darwin":
            return peak_memory / (1024 * 1024)
        return peak_memory / 1024

    def open_instructions(self):
        dialog = self._prepare_dialog(
            InstructionsDialog(self.language, self)
        )
        dialog.exec()
