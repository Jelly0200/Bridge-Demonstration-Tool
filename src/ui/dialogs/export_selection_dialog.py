from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from src.ui.i18n import show_message, translate_text


class ExportSelectionDialog(QDialog):
    def __init__(self, assets: list[dict], language="en", parent=None):
        super().__init__(parent)
        self.language = language
        self.setWindowTitle("Choose content to export")
        self.resize(620, 560)
        self._asset_items = []
        self._updating_checks = False

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Choose folders, cases, boards, and tests. "
                "Student accounts and results are never exported."
            )
        )
        self.asset_tree = QTreeWidget()
        self.asset_tree.setHeaderLabel("Available content")
        layout.addWidget(self.asset_tree)
        self._populate_assets(assets)
        self.asset_tree.itemChanged.connect(self._on_item_changed)

        form = QFormLayout()
        self.account_name_input = QLineEdit()
        self.account_name_input.setMaxLength(64)
        form.addRow("New administrator account:", self.account_name_input)
        self.account_password_input = QLineEdit()
        self.account_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("New account password:", self.account_password_input)
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Confirm new account password:", self.confirm_password_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept_selection)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate_assets(self, assets: list[dict]):
        folder_items = {
            asset["id"]: self._create_asset_item(asset)
            for asset in assets
            if asset["type"] == "folder"
        }
        case_items = {
            asset["id"]: self._create_asset_item(asset)
            for asset in assets
            if asset["type"] == "case"
        }
        for asset in assets:
            if asset["type"] != "folder":
                continue
            item = folder_items[asset["id"]]
            parent = folder_items.get(asset.get("parent_id"))
            if parent is None:
                self.asset_tree.addTopLevelItem(item)
            else:
                parent.addChild(item)

        for asset in assets:
            if asset["type"] == "case":
                folder_items[asset["folder_id"]].addChild(
                    case_items[asset["id"]]
                )
            elif asset["type"] == "board":
                case_items[asset["case_id"]].addChild(
                    self._create_asset_item(asset)
                )

        tests = [asset for asset in assets if asset["type"] == "test"]
        if tests:
            test_group = QTreeWidgetItem(
                self.asset_tree,
                [translate_text("Tests", self.language)],
            )
            test_group.setFlags(
                Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
            )
            for asset in tests:
                test_group.addChild(self._create_asset_item(asset))
        self.asset_tree.expandAll()

    def _create_asset_item(self, asset: dict) -> QTreeWidgetItem:
        item = QTreeWidgetItem([asset["name"]])
        item.setData(
            0,
            Qt.ItemDataRole.UserRole,
            (asset["type"], asset["id"]),
        )
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Unchecked)
        self._asset_items.append(item)
        return item

    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        if (
            self._updating_checks
            or column != 0
            or item.data(0, Qt.ItemDataRole.UserRole) is None
        ):
            return
        state = item.checkState(0)
        if state not in (Qt.CheckState.Checked, Qt.CheckState.Unchecked):
            return
        self._updating_checks = True
        try:
            pending = [item]
            while pending:
                parent = pending.pop()
                for index in range(parent.childCount()):
                    child = parent.child(index)
                    if child.data(0, Qt.ItemDataRole.UserRole) is not None:
                        child.setCheckState(0, state)
                        pending.append(child)
            parent = item.parent()
            while parent is not None:
                if parent.data(0, Qt.ItemDataRole.UserRole) is None:
                    break
                states = [
                    parent.child(index).checkState(0)
                    for index in range(parent.childCount())
                ]
                if all(value == Qt.CheckState.Checked for value in states):
                    parent.setCheckState(0, Qt.CheckState.Checked)
                elif all(value == Qt.CheckState.Unchecked for value in states):
                    parent.setCheckState(0, Qt.CheckState.Unchecked)
                else:
                    parent.setCheckState(0, Qt.CheckState.PartiallyChecked)
                parent = parent.parent()
        finally:
            self._updating_checks = False

    def selected_assets(self) -> dict[str, list[int]]:
        selection = {
            "folders": [],
            "cases": [],
            "boards": [],
            "tests": [],
        }
        selection_keys = {
            "folder": "folders",
            "case": "cases",
            "board": "boards",
            "test": "tests",
        }
        for item in self._asset_items:
            if item.checkState(0) != Qt.CheckState.Checked:
                continue
            asset_type, asset_id = item.data(0, Qt.ItemDataRole.UserRole)
            selection[selection_keys[asset_type]].append(asset_id)
        return selection

    def _accept_selection(self):
        if not any(self.selected_assets().values()):
            show_message(
                self,
                "warning",
                "Nothing selected",
                "Select at least one folder, case, board, or test to export.",
            )
            return
        if len(self.account_name_input.text().strip()) < 3:
            show_message(
                self,
                "warning",
                "Invalid account name",
                "The new administrator account name must have at least 3 characters.",
            )
            return
        password = self.account_password_input.text()
        if len(password) < 8:
            show_message(
                self,
                "warning",
                "Password too short",
                "The new administrator account password must have at least 8 characters.",
            )
            return
        if password != self.confirm_password_input.text():
            show_message(
                self,
                "warning",
                "Passwords do not match",
                "The new administrator account passwords do not match.",
            )
            return
        self.accept()

    def destination_account(self) -> dict:
        return {
            "name": self.account_name_input.text().strip(),
            "password": self.account_password_input.text(),
        }
