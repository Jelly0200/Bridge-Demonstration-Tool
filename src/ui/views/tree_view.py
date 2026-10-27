from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QHeaderView,
    QLineEdit,
    QStyledItemDelegate,
    QStyle,
    QTreeWidget,
    QTreeWidgetItem,
)

from src.database.repository import Repository
from src.ui.i18n import translate_text


class AssetNameDelegate(QStyledItemDelegate):
    def createEditor(self, parent, _option, _index):
        editor = QLineEdit(parent)
        editor.setMinimumHeight(32)
        return editor

    def updateEditorGeometry(self, editor, option, index):
        geometry = option.rect
        viewport = editor.parentWidget()
        available_width = viewport.width() - geometry.x()
        geometry.setWidth(max(geometry.width(), available_width))
        height = max(geometry.height(), editor.minimumHeight())
        geometry.setY(geometry.y() - (height - geometry.height()) // 2)
        geometry.setHeight(height)
        editor.setGeometry(geometry)


class TreeView(QTreeWidget):
    """Hierarchical tree view for folders, cases, boards, and scenarios."""
    node_selected = pyqtSignal(str, int)
    node_double_clicked = pyqtSignal(str, int)

    ASSET_PRESENTATION = {
        "folder": (
            QStyle.StandardPixmap.SP_DirIcon,
            "#fbbf24",
            "Folder asset",
        ),
        "case": (
            QStyle.StandardPixmap.SP_FileIcon,
            "#60a5fa",
            "Case asset",
        ),
        "board": (
            QStyle.StandardPixmap.SP_DriveHDIcon,
            "#c084fc",
            "Board asset",
        ),
        "scenario": (
            QStyle.StandardPixmap.SP_FileDialogInfoView,
            "#34d399",
            "Scenario asset",
        ),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabel("Asset tree (Folder / Case / Board / Scenario)")
        self.setMinimumWidth(320)
        self.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.setItemDelegateForColumn(0, AssetNameDelegate(self))
        self.current_language = "en"
        self.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        self.repo = Repository()
        self.currentItemChanged.connect(self.on_current_item_changed)
        self.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.load_tree_data(admin_id=None)

    def load_tree_data(self, admin_id: Optional[int]):
        self.clear()
        if admin_id is None:
            self._add_placeholder("Sign in or register to manage administrator assets.")
            return
        try:
            folders = self.repo.get_folders_by_admin(admin_id)
            if not folders:
                self._add_placeholder("No saved assets for this administrator.")
                return

            folders_by_id = {folder.id: folder for folder in folders}
            children = {}
            for folder in folders:
                children.setdefault(folder.parent_folder_id, []).append(folder)
            added_folder_ids = set()

            def add_folder(folder, parent_item=None):
                if folder.id in added_folder_ids:
                    return
                added_folder_ids.add(folder.id)
                if parent_item is None:
                    folder_item = QTreeWidgetItem(self, [folder.name])
                else:
                    folder_item = QTreeWidgetItem(parent_item, [folder.name])
                folder_item.setData(
                    0,
                    Qt.ItemDataRole.UserRole,
                    ("folder", folder.id),
                )
                self._style_asset_item(folder_item, "folder")
                folder_item.setFlags(folder_item.flags() | Qt.ItemFlag.ItemIsEditable)
                self._add_cases(folder_item, folder.id)
                for child_folder in children.get(folder.id, []):
                    add_folder(child_folder, folder_item)

            roots = [
                folder for folder in folders
                if folder.parent_folder_id not in folders_by_id
            ]
            for folder in roots:
                add_folder(folder)
            for folder in folders:
                if folder.id not in added_folder_ids:
                    add_folder(folder)

            self.expandAll()
        except Exception as error:
            self._add_placeholder(f"Unable to load assets: {error}")

    def _add_cases(self, folder_item: QTreeWidgetItem, folder_id: int):
        for case in self.repo.get_cases_by_folder(folder_id):
            case_item = QTreeWidgetItem(folder_item, [case.name])
            case_item.setData(0, Qt.ItemDataRole.UserRole, ("case", case.id))
            self._style_asset_item(case_item, "case")
            case_item.setFlags(case_item.flags() | Qt.ItemFlag.ItemIsEditable)

            for board in self.repo.get_boards_by_case(case.id):
                board_name = board.description or f"Board #{board.id}"
                board_item = QTreeWidgetItem(case_item, [board_name])
                board_item.setData(0, Qt.ItemDataRole.UserRole, ("board", board.id))
                self._style_asset_item(board_item, "board")

                for scenario in self.repo.get_scenarios_by_board(board.id):
                    scenario_name = scenario.name.strip() or f"Scenario #{scenario.id}"
                    scenario_item = QTreeWidgetItem(
                        board_item,
                        [scenario_name],
                    )
                    scenario_item.setData(
                        0,
                        Qt.ItemDataRole.UserRole,
                        ("scenario", scenario.id),
                    )
                    self._style_asset_item(scenario_item, "scenario")
                    scenario_item.setFlags(
                        scenario_item.flags() | Qt.ItemFlag.ItemIsEditable
                    )

    def filter_items(self, query: str):
        query = query.strip().casefold()
        for index in range(self.topLevelItemCount()):
            self._filter_item(self.topLevelItem(index), query)

    def _filter_item(self, item: QTreeWidgetItem, query: str) -> bool:
        text_matches = query in item.text(0).casefold()
        child_matches = False
        for index in range(item.childCount()):
            child_matches = self._filter_item(item.child(index), query) or child_matches
        visible = not query or text_matches or child_matches
        item.setHidden(not visible)
        return visible

    def _add_placeholder(self, text: str):
        item = QTreeWidgetItem(self, [text])
        item.setData(0, Qt.ItemDataRole.UserRole + 1, text)
        item.setText(0, translate_text(text, self.current_language))
        item.setFlags(Qt.ItemFlag.NoItemFlags)

    def _style_asset_item(self, item: QTreeWidgetItem, asset_type: str):
        presentation = self.ASSET_PRESENTATION.get(asset_type)
        if presentation is None:
            return
        icon, color, tooltip = presentation
        item.setIcon(0, self.style().standardIcon(icon))
        item.setForeground(0, QBrush(QColor(color)))
        item.setToolTip(0, translate_text(tooltip, self.current_language))

    def set_language(self, language: str):
        self.current_language = language
        self.setHeaderLabel(
            translate_text(
                "Asset tree (Folder / Case / Board / Scenario)",
                language,
            )
        )
        def update_item(item):
            placeholder = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if placeholder:
                item.setText(0, translate_text(placeholder, language))
                return
            asset = item.data(0, Qt.ItemDataRole.UserRole)
            if asset:
                self._style_asset_item(item, asset[0])
            for child_index in range(item.childCount()):
                update_item(item.child(child_index))

        for index in range(self.topLevelItemCount()):
            update_item(self.topLevelItem(index))

    def on_current_item_changed(
        self,
        item: Optional[QTreeWidgetItem],
        _previous_item: Optional[QTreeWidgetItem],
    ):
        if item is None:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data:
            node_type, node_id = data
            self.node_selected.emit(node_type, node_id)

    def on_item_double_clicked(self, item: QTreeWidgetItem, _column: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data:
            node_type, node_id = data
            self.node_double_clicked.emit(node_type, node_id)