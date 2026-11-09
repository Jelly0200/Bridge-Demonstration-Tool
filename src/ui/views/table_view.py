import copy
import json
from pathlib import Path
from typing import Any, Optional

from PyQt6.QtCore import (
    QPropertyAnimation,
    QPoint,
    QRect,
    QTimer,
    Qt,
    QUrl,
    pyqtSignal,
)
from PyQt6.QtGui import QAction, QActionGroup, QColor, QFont, QResizeEvent
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSlider,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QFrame,
)

from src.core.bridge_game import BridgeGameEngine
from src.core.bridge_logic import BridgeLogic
from src.core.pbn_parser import PbnParser
from src.core.dds_wrapper import DdsWrapper
from src.robot.robot_agent import RobotAgent
from src.robot.label_evaluator import DEFAULT_COLOR_JOBS, LabelEvaluator
from src.ui.widgets.bidding_box import BiddingBoxDialog
from src.ui.widgets.hand_widget import CardWidget, HandWidget
from src.ui.dialogs.label_color_dialog import LabelColorDialog
from src.ui.dialogs.label_jobs_dialog import LabelDefinitionDialog
from src.ui.dialogs.test_scenario_dialog import TestScenarioDialog
from src.ui.i18n import (
    BilingualTextController,
    exec_and_delete,
    show_message,
    translate_text,
)
from config.constants import RANKS, SUITS


class TableView(QWidget):
    """Interactive bridge table for saved boards and scenarios."""

    CARD_AREA_VERTICAL_CLEARANCE = 190

    mode_changed = pyqtSignal(str)
    scenario_completed = pyqtSignal()
    scenario_changed = pyqtSignal()
    preferences_changed = pyqtSignal()
    font_style_changed = pyqtSignal()

    SEATS_CLOCKWISE = ["NORTH", "EAST", "SOUTH", "WEST"]
    SEAT_LABELS = {
        "NORTH": "NORTH",
        "EAST": "EAST",
        "SOUTH": "SOUTH",
        "WEST": "WEST",
    }
    SEAT_PBN_ATTRIBUTES = {
        "NORTH": "north_hand_pbn",
        "EAST": "east_hand_pbn",
        "SOUTH": "south_hand_pbn",
        "WEST": "west_hand_pbn",
    }
    PARTNERS = {
        "NORTH": {"NORTH", "SOUTH"},
        "SOUTH": {"NORTH", "SOUTH"},
        "EAST": {"EAST", "WEST"},
        "WEST": {"EAST", "WEST"},
    }
    VALID_SUITS = set("SHDC")
    VALID_RANKS = set("23456789TJQKA")
    DDS_SEATS = ("NORTH", "EAST", "SOUTH", "WEST")
    DDS_STRAINS = ("S", "H", "D", "C", "NT")
    DDS_TRUMPS = {"S": 0, "H": 1, "D": 2, "C": 3, "NT": 4}
    DDS_MATRIX_SEATS = ("NORTH", "SOUTH", "WEST", "EAST")
    ROBOT_MOVE_DELAY_MS = 1200
    ROBOT_CARD_ANIMATION_MS = 320
    TEST_CARD_SIZE_PX = 50
    TEST_ROBOT_MOVE_DELAY_MS = 1200
    TEST_SOUND_VOLUME_PERCENT = 50
    RECORD_BUTTON_DDS_GAP = 12

    def __init__(
        self,
        parent=None,
        language_controller: Optional[BilingualTextController] = None,
    ):
        super().__init__(parent)
        self.setObjectName("centralTablePanel")
        self.language_controller = (
            language_controller or BilingualTextController()
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.perspective = "SOUTH"
        self.current_side = "SOUTH"
        self.current_mode = "NORMAL"
        self.view_mode = "ANALYSIS"
        self.preferred_view_mode = "ANALYSIS"
        self.board = None
        self.configuration = None
        self.scenario = None
        self.game: Optional[BridgeGameEngine] = None
        self.robot: Optional[RobotAgent] = None
        self.labels: list[dict[str, Any]] = []
        self.target_sequence: list[str] = []
        self.target_index = 0
        self.move_history: list[tuple[BridgeGameEngine, int, int]] = []
        self.bidding_route: list[str] = []
        self.rule_mode = "LABEL"
        self.label_jobs = copy.deepcopy(DEFAULT_COLOR_JOBS)
        self.robot_error_message: Optional[str] = None
        self.demonstration_result_shown = False
        self.dds_display_mode = "TRICKS"
        self.dds_matrix_hidden = False
        self.robot_move_delay_ms = self.ROBOT_MOVE_DELAY_MS
        self.card_size = 50
        self.suit_symbol_size = 30
        self.application_font_size = 15
        self.application_font_color = "#e2e8f0"
        self.application_background_color = "#0b1120"
        self.central_panel_height_px = 600
        self.dds_trick_table: Optional[list[list[int]]] = None
        self.dds_card_scores: dict[str, int] = {}
        self.lockdown_mode = False
        self.test_playback_active = False
        self._test_playback_appearance_active = False
        self._completion_emitted = False
        self.dds_wrapper = DdsWrapper()
        self.robot_timer = QTimer(self)
        self.robot_timer.setSingleShot(True)
        self.robot_timer.timeout.connect(self._play_next_robot_move)
        self.robot_animation: Optional[QPropertyAnimation] = None
        self.robot_animation_destination: Optional[QWidget] = None
        self.robot_card_sound_choice = "CLASSIC"
        self.robot_card_sound_enabled = True
        self.sound_volume_percent = 35
        self.robot_card_sound = QSoundEffect(self)
        self.robot_sound_paths = {
            "CLASSIC": "robot_card.wav",
        }
        self._set_robot_card_sound_source("CLASSIC")
        self._set_sound_volume(self.sound_volume_percent)
        self.robot_card_sound_action = QAction(
            "Play card sound",
            self,
        )
        self.robot_card_sound_action.setCheckable(True)
        self.robot_card_sound_action.setChecked(True)
        self.robot_card_sound_action.toggled.connect(
            self.set_robot_card_sound_enabled
        )
        self.card_size_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.card_size_slider.setRange(35, 50)
        self.card_size_slider.setSingleStep(1)
        self.card_size_slider.setPageStep(4)
        self.card_size_slider.setTickInterval(4)
        self.card_size_slider.setTickPosition(
            QSlider.TickPosition.TicksBelow
        )
        self.card_size_slider.setTracking(False)
        self.card_size_slider.setValue(self.card_size)
        self.card_size_slider.valueChanged.connect(self.set_card_size)
        self.suit_symbol_size_slider = QSlider(
            Qt.Orientation.Horizontal,
            self,
        )
        self.suit_symbol_size_slider.setRange(10, 35)
        self.suit_symbol_size_slider.setSingleStep(1)
        self.suit_symbol_size_slider.setPageStep(4)
        self.suit_symbol_size_slider.setTickInterval(4)
        self.suit_symbol_size_slider.setTickPosition(
            QSlider.TickPosition.TicksBelow
        )
        self.suit_symbol_size_slider.setTracking(False)
        self.suit_symbol_size_slider.setValue(self.suit_symbol_size)
        self.suit_symbol_size_slider.valueChanged.connect(
            self.set_suit_symbol_size
        )
        self.font_size_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.font_size_slider.setRange(10, 24)
        self.font_size_slider.setSingleStep(1)
        self.font_size_slider.setPageStep(2)
        self.font_size_slider.setTracking(False)
        self.font_size_slider.setValue(self.application_font_size)
        self.font_size_slider.valueChanged.connect(
            self.set_application_font_size
        )
        self.robot_speed_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.robot_speed_slider.setRange(300, 3000)
        self.robot_speed_slider.setSingleStep(100)
        self.robot_speed_slider.setPageStep(300)
        self.robot_speed_slider.setTickInterval(900)
        self.robot_speed_slider.setTickPosition(
            QSlider.TickPosition.TicksBelow
        )
        self.robot_speed_slider.setInvertedAppearance(True)
        self.robot_speed_slider.setValue(self.robot_move_delay_ms)
        self.robot_speed_slider.valueChanged.connect(self.set_robot_speed)
        self.sound_volume_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.sound_volume_slider.setRange(0, 100)
        self.sound_volume_slider.setSingleStep(1)
        self.sound_volume_slider.setPageStep(10)
        self.sound_volume_slider.setTickInterval(20)
        self.sound_volume_slider.setTickPosition(
            QSlider.TickPosition.TicksBelow
        )
        self.sound_volume_slider.setValue(self.sound_volume_percent)
        self.sound_volume_slider.valueChanged.connect(self.set_sound_volume)
        self.init_ui()
        self.language_controller.install(self)

    def _build_bidding_menu(self):
        self.bidding_action = self.bidding_menu.addAction(
            "Bidding", self.open_settings
        )
        self.description_action = self.bidding_menu.addAction(
            "Information", self.show_description
        )

        view_group = QActionGroup(self)
        view_group.setExclusive(True)
        self.view_actions = {}
        for mode, title in (("ANALYSIS", "Analysis"), ("HIDDEN", "Hidden")):
            action = QAction(title, self)
            action.setCheckable(True)
            action.setChecked(mode == self.view_mode)
            view_group.addAction(action)
            action.triggered.connect(
                lambda checked, selected_mode=mode: (
                    self.set_view_mode(selected_mode)
                    if checked
                    else None
                )
            )
            self.view_actions[mode] = action

        dds_group = QActionGroup(self)
        dds_group.setExclusive(True)
        self.dds_mode_actions = {}
        for mode, title in (
            ("TRICKS", "Tricks"),
            ("CONTRACT_OFFSET", "Contract tricks"),
        ):
            action = QAction(title, self)
            action.setObjectName(f"dds_mode_{mode.lower()}")
            action.setCheckable(True)
            action.setChecked(mode == self.dds_display_mode)
            dds_group.addAction(action)
            action.triggered.connect(
                lambda checked, selected_mode=mode: (
                    self.set_dds_display_mode(selected_mode)
                    if checked
                    else None
                )
            )
            self.dds_mode_actions[mode] = action

        self.dds_visibility_action = QAction("Show DDS matrix", self)
        self.dds_visibility_action.setObjectName("dds_visibility_action")
        self.dds_visibility_action.setCheckable(True)
        self.dds_visibility_action.setChecked(not self.dds_matrix_hidden)
        self.dds_visibility_action.toggled.connect(
            self.set_dds_matrix_visible
        )

        rule_group = QActionGroup(self)
        rule_group.setExclusive(True)
        self.rule_actions = {}
        for mode, title in (
            ("TARGET", "Follow recorded sequence"),
            ("LABEL", "Follow labels"),
        ):
            action = QAction(title, self)
            action.setCheckable(True)
            action.setChecked(mode == self.rule_mode)
            rule_group.addAction(action)
            action.triggered.connect(
                lambda checked, selected_mode=mode: (
                    self.set_rule_mode(selected_mode)
                    if checked
                    else None
                )
            )
            self.rule_actions[mode] = action

        self.label_action = QAction("Label.md", self)
        self.label_action.triggered.connect(self.show_label_instructions)

        self.rotate_action = QAction("Rotate view", self)
        self.rotate_action.triggered.connect(self.rotate_perspective)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.top_bar_widget = QWidget(self)
        self.top_bar_widget.setObjectName("upperTablePanel")
        self.top_bar_layout = QHBoxLayout(self.top_bar_widget)
        self.top_bar_layout.setContentsMargins(0, 0, 0, 0)
        top_bar_layout = self.top_bar_layout
        self.btn_bidding = QPushButton("Bidding")
        self.bidding_menu = QMenu(self.btn_bidding)
        self.btn_bidding.setMenu(self.bidding_menu)
        self._build_bidding_menu()
        top_alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        top_bar_layout.addWidget(self.btn_bidding, alignment=top_alignment)

        self.btn_demonstration = QPushButton("Start")
        self.btn_demonstration.setStyleSheet(
            "background-color: #2e8b57; color: white; font-weight: bold;"
        )
        self.btn_demonstration.clicked.connect(self.toggle_demonstration)
        top_bar_layout.addWidget(
            self.btn_demonstration,
            alignment=Qt.AlignmentFlag.AlignTop,
        )
        top_bar_layout.addStretch()
        self.btn_bidding.setEnabled(False)
        layout.addWidget(self.top_bar_widget)
        layout.addStretch(1)

        self.table_grid = QGridLayout()
        self.table_canvas = QWidget(self)
        self.table_canvas.setLayout(self.table_grid)
        self.table_grid.setSpacing(8)
        self.table_grid.setContentsMargins(0, 0, 0, 0)
        self.hand_widgets = {
            seat: HandWidget(
                seat,
                card_size_large=True,
                suit_symbol_size=self.suit_symbol_size,
            )
            for seat in self.SEATS_CLOCKWISE
        }
        for seat, hand in self.hand_widgets.items():
            hand.card_selected.connect(
                lambda card, player=seat: self.on_card_selected(player, card)
            )
            hand.card_context_requested.connect(self.on_card_context_requested)
        self.seat_labels = {
            seat: QLabel(self.SEAT_LABELS[seat])
            for seat in self.SEATS_CLOCKWISE
        }
        self.seat_containers = {}
        self.seat_layouts = {}
        for label in self.seat_labels.values():
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFont(QFont(label.font().family(), 16, QFont.Weight.Bold))
        for seat in self.SEATS_CLOCKWISE:
            seat_layout = QVBoxLayout()
            seat_layout.setContentsMargins(2, 2, 2, 2)
            seat_layout.setSpacing(2)
            seat_layout.addWidget(self.seat_labels[seat])
            seat_layout.addWidget(
                self.hand_widgets[seat],
                alignment=Qt.AlignmentFlag.AlignCenter,
            )
            container = QWidget()
            container.setLayout(seat_layout)
            self.seat_containers[seat] = container
            self.seat_layouts[seat] = seat_layout

        self.trick_area = QWidget()
        self.trick_grid = QGridLayout(self.trick_area)
        self.trick_grid.setContentsMargins(0, 0, 0, 0)
        self.trick_grid.setSpacing(0)
        self.trick_grid.setRowStretch(0, 1)
        self.trick_grid.setColumnStretch(0, 1)
        self.played_card_area = QWidget(self.trick_area)
        self.played_card_area.setFixedSize(164, 224)
        self.played_cards_grid = QGridLayout(self.played_card_area)
        self.played_cards_grid.setContentsMargins(0, 0, 0, 0)
        self.played_cards_grid.setSpacing(4)
        for index in range(3):
            self.played_cards_grid.setRowStretch(index, 1)
            self.played_cards_grid.setColumnStretch(index, 1)
        self.trick_grid.addWidget(
            self.played_card_area,
            0,
            0,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        self.info_overlay = QWidget(self)
        self.info_overlay.setFixedHeight(72)
        self.info_overlay.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        info_overlay_layout = QHBoxLayout(self.info_overlay)
        info_overlay_layout.setContentsMargins(0, 0, 0, 0)
        info_overlay_layout.addStretch()
        self.center_info = QLabel(
            "Select a scenario to view its key play signal.",
            self.info_overlay,
        )
        self.center_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.center_info.setMinimumHeight(66)
        self.center_info.setWordWrap(True)
        self.center_info.setMaximumWidth(460)
        self.center_info.setStyleSheet(
            "background-color: rgba(15, 23, 42, 238); "
            "border: 1px solid rgba(56, 189, 248, 170); "
            "border-radius: 10px; padding: 8px 14px; "
            "color: #f8fafc; font-weight: 600;"
        )
        info_overlay_layout.addWidget(
            self.center_info,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter,
        )
        info_overlay_layout.addStretch()
        self.trick_area.setFixedSize(268, 244)
        self.trick_grid.activate()
        self.played_card_widgets = {}
        self._played_card_widget_pool = {}

        for row in range(3):
            self.table_grid.setRowStretch(row, 1)
        for column, stretch in enumerate((2, 1, 2)):
            self.table_grid.setColumnStretch(column, stretch)

        self.footer_controls = QWidget(self)
        footer_layout = QHBoxLayout(self.footer_controls)
        self.footer_layout = footer_layout
        footer_layout.setContentsMargins(0, 0, 0, 0)
        self.navigation_controls = QFrame(self)
        self.navigation_controls.setObjectName("moveNavigationControls")
        self.navigation_controls.setFrameShape(QFrame.Shape.StyledPanel)
        self.navigation_controls.setStyleSheet(
            "#moveNavigationControls { background-color: #111827; "
            "border: 1px solid #475569; border-radius: 6px; } "
            "#moveNavigationControls QPushButton { color: #f8fafc; "
            "background-color: #334155; border: 1px solid #64748b; "
            "border-radius: 4px; padding: 4px 10px; } "
            "#moveNavigationControls QPushButton:disabled { "
            "color: #cbd5e1; background-color: #1e293b; "
            "border-color: #475569; }"
        )
        navigation_layout = QHBoxLayout(self.navigation_controls)
        navigation_layout.setContentsMargins(6, 4, 6, 4)
        navigation_layout.setSpacing(6)
        self.btn_prev = QPushButton("Last move")
        self.btn_next = QPushButton("Next move")
        self.btn_reset = QPushButton("Reset")
        self.btn_prev.clicked.connect(self.play_previous_move)
        self.btn_next.clicked.connect(self.play_next_move)
        self.btn_reset.clicked.connect(self.reset_moves)
        bottom_alignment = Qt.AlignmentFlag.AlignBottom
        navigation_layout.addWidget(self.btn_prev)
        navigation_layout.addWidget(self.btn_reset)
        navigation_layout.addWidget(self.btn_next)
        footer_layout.addWidget(
            self.navigation_controls,
            alignment=bottom_alignment,
        )
        footer_layout.addStretch()
        self.dds_result_table = QTableWidget(4, 5)
        self.dds_result_table.setObjectName("dds_result_table")
        self.dds_result_table.setHorizontalHeaderLabels(["S", "H", "D", "C", "NT"])
        self.dds_result_table.setVerticalHeaderLabels(["N", "S", "W", "E"])
        horizontal_header = self.dds_result_table.horizontalHeader()
        if horizontal_header is not None:
            horizontal_header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        vertical_header = self.dds_result_table.verticalHeader()
        if vertical_header is not None:
            vertical_header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.dds_result_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.dds_result_table.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        self.dds_result_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.dds_result_table.setAlternatingRowColors(True)
        self.dds_result_table.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.dds_result_table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.dds_result_table.setFixedSize(310, 180)
        self.dds_result_table.setStyleSheet(
            "QTableWidget { background-color: #111827; color: #e2e8f0; "
            "gridline-color: #334155; border: 1px solid #334155; "
            "border-radius: 8px; alternate-background-color: #1e293b; } "
            "QTableWidget::item { padding: 3px; font-weight: bold; } "
            "QHeaderView::section { background-color: #1e293b; "
            "color: #7dd3fc; padding: 4px; border: none; "
            "font-weight: bold; } "
            "QTableCornerButton::section { background-color: #1e3a8a; "
            "border: 1px solid #334155; }"
        )
        self.dds_slot = QStackedWidget(self)
        self.dds_slot.setFixedSize(310, 180)
        self.dds_slot.addWidget(self.dds_result_table)
        self.dds_slot.addWidget(QWidget())

        self.btn_record = QPushButton("Record target", self)
        self.btn_record.clicked.connect(self.record_completed_play)
        self.btn_record.setEnabled(False)
        self.btn_record.hide()
        self.btn_human_seat = QPushButton("Human seat: SOUTH")
        self.btn_human_seat.clicked.connect(self.select_side)
        footer_layout.addWidget(
            self.btn_human_seat,
            alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight,
        )
        self._clear_dds_result_matrix()

        self._place_seats()
        self._render_played_cards()
        self._update_table_canvas_size()
        self._update_dds_visibility()
        self._update_scenario_controls()

    def get_admin_preferences(self) -> dict[str, Any]:
        return {
            "card_size_px": self.card_size,
            "card_suit_symbol_size_px": self.suit_symbol_size,
            "font_size_px": self.application_font_size,
            "font_color": self.application_font_color,
            "background_color": self.application_background_color,
            "robot_delay_ms": self.robot_move_delay_ms,
            "sound_choice": self.robot_card_sound_choice,
            "sound_volume_percent": self.sound_volume_percent,
            "dds_matrix_hidden": self.dds_matrix_hidden,
            "dds_display_mode": self.dds_display_mode,
            "view_mode": self.preferred_view_mode,
            "perspective": self.perspective,
            "human_seat": self.current_side,
            "label_jobs": copy.deepcopy(self.label_jobs),
        }

    def apply_admin_preferences(self, preferences: dict[str, Any]):
        self.set_card_size(preferences["card_size_px"])
        self.set_suit_symbol_size(preferences.get("card_suit_symbol_size_px", 30))
        self.set_application_font_size(preferences["font_size_px"])
        self.set_application_font_color(preferences["font_color"])
        self.set_application_background_color(
            preferences.get("background_color", "#0b1120")
        )
        self.set_robot_speed(preferences["robot_delay_ms"])
        self.set_robot_card_sound_choice(preferences["sound_choice"])
        self.set_sound_volume(preferences["sound_volume_percent"])
        self.dds_matrix_hidden = preferences["dds_matrix_hidden"]
        self.dds_visibility_action.setChecked(not self.dds_matrix_hidden)
        self.dds_display_mode = preferences["dds_display_mode"]
        self.dds_mode_actions[self.dds_display_mode].setChecked(True)
        self.preferred_view_mode = preferences["view_mode"]
        self.view_mode = self.preferred_view_mode
        self.view_actions[self.view_mode].setChecked(True)
        self.perspective = preferences["perspective"]
        self.current_side = preferences["human_seat"]
        self.label_jobs = LabelEvaluator.normalize_color_jobs(
            preferences["label_jobs"]
        )
        if self.robot is not None:
            self.robot.color_jobs = copy.deepcopy(self.label_jobs)
        self._place_seats()
        self._render_hands()
        self._update_table_canvas_size()
        self._render_dds_result_matrix()
        self._update_dds_visibility()
        self._update_center_info()
        self._update_lockdown_controls()

    def set_application_font_size(self, size: int):
        if type(size) is not int or not 10 <= size <= 24:
            raise ValueError(f"Unsupported application font size: {size}")
        changed = self.application_font_size != size
        self.application_font_size = size
        if self.font_size_slider.value() != size:
            self.font_size_slider.setValue(size)
        if changed:
            self.font_style_changed.emit()
            self.preferences_changed.emit()

    def set_central_panel_height(self, height: int):
        if type(height) is not int or not 400 <= height <= 1200:
            raise ValueError(f"Unsupported central panel height: {height}")
        changed = self.central_panel_height_px != height
        self.central_panel_height_px = height
        if changed:
            self._update_table_canvas_size()
            self.preferences_changed.emit()

    def set_application_font_color(self, color: str):
        parsed_color = QColor(color)
        if not parsed_color.isValid():
            raise ValueError(f"Unsupported application font color: {color}")
        normalized_color = parsed_color.name()
        changed = self.application_font_color != normalized_color
        self.application_font_color = normalized_color
        if changed:
            self.font_style_changed.emit()
            self.preferences_changed.emit()

    def set_application_background_color(self, color: str):
        parsed_color = QColor(color)
        if not parsed_color.isValid():
            raise ValueError(
                f"Unsupported application background color: {color}"
            )
        normalized_color = parsed_color.name()
        changed = self.application_background_color != normalized_color
        self.application_background_color = normalized_color
        if changed:
            self.font_style_changed.emit()
            self.preferences_changed.emit()

    def _update_table_canvas_size(self):
        for hand in self.hand_widgets.values():
            hand.main_layout.invalidate()
            hand.main_layout.activate()
        for container in self.seat_containers.values():
            container.layout().invalidate()
            container.layout().activate()
        horizontal_seats = [
            self.seat_containers[seat]
            for seat in self.SEATS_CLOCKWISE
            if self.hand_widgets[seat].horizontal
        ]
        vertical_seats = [
            self.seat_containers[seat]
            for seat in self.SEATS_CLOCKWISE
            if not self.hand_widgets[seat].horizontal
        ]
        horizontal_sizes = [
            container.sizeHint().expandedTo(container.minimumSizeHint())
            for container in horizontal_seats
        ]
        vertical_sizes = [
            container.sizeHint().expandedTo(container.minimumSizeHint())
            for container in vertical_seats
        ]
        horizontal_width = max(size.width() for size in horizontal_sizes)
        side_width = sum(size.width() for size in vertical_sizes)
        middle_height = max(
            max(size.height() for size in vertical_sizes),
            self.trick_area.height(),
        )
        spacing = self.table_grid.spacing()
        canvas_height = (
            sum(size.height() for size in horizontal_sizes)
            + middle_height
            + 2 * spacing
        )
        minimum_width = max(
            self.dds_slot.width(),
            horizontal_width,
            side_width + self.trick_area.width() + 2 * spacing,
        )
        self.table_canvas.setFixedHeight(canvas_height)
        minimum_height = max(
            canvas_height + 2 * self.CARD_AREA_VERTICAL_CLEARANCE,
            self.central_panel_height_px,
        )
        if (
            self.minimumWidth() != minimum_width
            or self.minimumHeight() != minimum_height
        ):
            self.setMinimumSize(minimum_width, minimum_height)
        self._position_overlay_widgets()
        self.table_grid.invalidate()
        self.table_grid.activate()

    def _position_overlay_widgets(self):
        canvas_y = (self.height() - self.table_canvas.height()) // 2
        self.table_canvas.setGeometry(
            0,
            canvas_y,
            self.width(),
            self.table_canvas.height(),
        )
        self.table_canvas.lower()
        overlay_height = (
            self.info_overlay.height()
            if self.test_playback_active
            else 64
        )
        self.info_overlay.setGeometry(
            0,
            0,
            self.width(),
            overlay_height,
        )
        self.dds_slot.move(
            max(0, self.width() - self.dds_slot.width()),
            0,
        )
        if hasattr(self, "btn_record"):
            self.btn_record.adjustSize()
            record_y = (
                self.dds_result_table.mapTo(
                    self,
                    QPoint(0, self.dds_result_table.height()),
                ).y() + self.RECORD_BUTTON_DDS_GAP
                if self.dds_slot.currentIndex() == 0
                else 0
            )
            self.btn_record.setGeometry(
                self.width() - self.btn_record.width(),
                record_y,
                self.btn_record.width(),
                self.btn_record.height(),
            )
            self.btn_record.raise_()
        visible_rect = self.rect()
        ancestor = self.parentWidget()
        while ancestor is not None:
            ancestor_rect = QRect(
                self.mapFromGlobal(
                    ancestor.mapToGlobal(ancestor.rect().topLeft())
                ),
                ancestor.size(),
            )
            visible_rect = visible_rect.intersected(ancestor_rect)
            if visible_rect.isEmpty():
                return
            ancestor = ancestor.parentWidget()
        footer_height = min(
            self.footer_controls.sizeHint().height(),
            visible_rect.height(),
        )
        self.footer_controls.setGeometry(
            visible_rect.left(),
            visible_rect.bottom() - footer_height + 1,
            visible_rect.width(),
            footer_height,
        )
        self.info_overlay.raise_()
        self.dds_slot.raise_()
        self.btn_bidding.raise_()
        self.btn_demonstration.raise_()
        self.navigation_controls.raise_()
        self.btn_record.raise_()
        self.btn_human_seat.raise_()
        self.footer_controls.raise_()

    def resizeEvent(self, event: QResizeEvent | None) -> None:
        super().resizeEvent(event)
        if hasattr(self, "info_overlay"):
            self._position_overlay_widgets()

    def load_board(
        self,
        board,
        configuration,
        scenario=None,
        labels=None,
        *,
        force_robot=False,
        test_playback=False,
    ):
        """Load a saved board and, optionally, a scenario onto the table."""
        if configuration is None:
            raise ValueError("The selected board has no configuration.")
        if scenario and scenario.board_id != board.id:
            raise ValueError("The selected scenario does not belong to this board.")
        hands = {
            seat: getattr(board, attribute)
            for seat, attribute in self.SEAT_PBN_ATTRIBUTES.items()
        }
        if not PbnParser.validate_deal(hands):
            raise ValueError(f"Board {board.id} does not contain a valid 52-card deal.")

        normalized_labels = self._normalize_labels(labels or [])
        game = BridgeGameEngine(
            hands,
            dealer=configuration.dealer,
            vulnerability=configuration.vulnerability,
        )
        bidding_route = self._parse_bidding_route(
            scenario.bidding_route if scenario else ""
        )
        bidding_route = [
            self._normalize_auction_call(call) for call in bidding_route
        ]
        risk_status = BridgeLogic.derive_risk_status(bidding_route)
        target_sequence = []
        robot = None
        contract = ""
        declarer = configuration.dealer
        if scenario:
            scenario.risk_status = risk_status
            if scenario.targeted_sequence:
                target_sequence = self._parse_target_sequence(
                    scenario.targeted_sequence
                )
            contract, declarer, auction_complete = self._derive_contract(
                game,
                bidding_route,
            )
            scenario.contract = contract
            scenario.declarer = declarer
            if auction_complete and contract != "PASSED_OUT":
                game.start_play(contract, declarer, scenario.risk_status)
                if not scenario.is_targeted or force_robot:
                    robot = RobotAgent(
                        game,
                        self.dds_wrapper,
                        color_jobs=self.label_jobs,
                    )

        self._stop_robot_playback()
        self.board = board
        self.configuration = configuration
        self.scenario = scenario
        self.test_playback_active = test_playback
        self._apply_test_playback_appearance()
        self._completion_emitted = False
        self.labels = normalized_labels
        self.current_mode = "NORMAL"
        self.view_mode = self.preferred_view_mode
        self.rule_mode = "TARGET" if scenario and scenario.is_targeted else "LABEL"
        self.robot_error_message = None
        self.demonstration_result_shown = False
        self.dds_card_scores = {}
        self.move_history.clear()
        self.target_index = 0
        self.target_sequence = target_sequence
        self.game = game
        self.robot = robot
        self.bidding_route = bidding_route

        self.view_actions[self.view_mode].setChecked(True)
        self.rule_actions[self.rule_mode].setChecked(True)
        self._refresh_dds_result(hands)
        self._render_hands()
        self._update_table_canvas_size()
        self._update_navigation()
        self._update_scenario_controls()
        self._update_center_info()
        self._update_lockdown_controls()
        if test_playback:
            self._apply_test_playback_preferences()

    def set_lockdown_mode(self, enabled: bool):
        self.lockdown_mode = enabled
        self._update_lockdown_controls()

    def _update_lockdown_controls(self):
        if not hasattr(self, "top_bar_layout"):
            return
        lockdown = self.lockdown_mode
        for button in (
            self.btn_demonstration,
            self.btn_record,
        ):
            button.setVisible(not lockdown)
        self.btn_bidding.setVisible(True)
        self.btn_prev.setVisible(True)
        self.btn_next.setVisible(True)
        if lockdown:
            self.view_mode = "HIDDEN"
            self.view_actions["HIDDEN"].setChecked(True)
            self._apply_view_mode()
        self._update_scenario_controls()
        self._update_dds_visibility()

    def clear_board(self):
        """Remove loaded deal data when the active administrator signs out."""
        self._stop_robot_playback()
        self.board = None
        self.configuration = None
        self.scenario = None
        self.game = None
        self.robot = None
        self.labels = []
        self.target_sequence = []
        self.move_history.clear()
        self.target_index = 0
        self.bidding_route = []
        self.test_playback_active = False
        self._apply_test_playback_appearance()
        self.current_side = "SOUTH"
        self.current_mode = "NORMAL"
        self.view_mode = "ANALYSIS"
        self.rule_mode = "LABEL"
        self.robot_error_message = None
        self.demonstration_result_shown = False
        self.dds_trick_table = None
        self.dds_card_scores = {}
        self.view_actions["ANALYSIS"].setChecked(True)
        self.rule_actions["LABEL"].setChecked(True)
        self._clear_dds_result_matrix()
        self._render_hands()
        self._update_table_canvas_size()
        self._update_navigation()
        self._update_scenario_controls()
        self._update_center_info()

    @classmethod
    def _normalize_card_code(cls, card: str) -> str:
        code = str(card).strip().upper()
        if len(code) != 2:
            raise ValueError(f"Invalid card code: {card}")
        if code[0] in cls.VALID_SUITS and code[1] in cls.VALID_RANKS:
            return code
        if code[1] in cls.VALID_SUITS and code[0] in cls.VALID_RANKS:
            return code[1] + code[0]
        raise ValueError(f"Invalid card code: {card}")

    @classmethod
    def _normalize_labels(cls, labels) -> list[dict[str, Any]]:
        normalized = []
        for label in labels:
            if isinstance(label, dict):
                sequence = label["Sequence"]
                color = label["Color"]
                card_code = label["Card"]
            else:
                sequence = label.sequence
                color = label.color
                card_code = label.card
            card = cls._normalize_card_code(card_code)
            normalized.append({
                "Sequence": sequence,
                "Color": color.upper(),
                "Card": card,
            })
        return normalized

    @classmethod
    def _parse_target_sequence(cls, raw_sequence: Optional[str]) -> list[str]:
        if not raw_sequence:
            return []
        sequence = json.loads(raw_sequence)
        if isinstance(sequence, dict):
            sequence = sequence.get("cards", sequence.get("sequence"))
        if not isinstance(sequence, list):
            raise ValueError("The target sequence must be a JSON list of card codes.")
        return [cls._normalize_card_code(card) for card in sequence]

    @staticmethod
    def _parse_bidding_route(route: str) -> list[str]:
        if not route:
            return []
        try:
            decoded = json.loads(route)
            if isinstance(decoded, list):
                return [str(call).strip().upper() for call in decoded]
        except json.JSONDecodeError:
            pass
        return [
            call.strip().upper()
            for call in route.replace("→", " ").replace(",", " ").split()
            if call.strip()
        ]

    @staticmethod
    def _normalize_auction_call(call: str) -> str:
        parsed = BridgeLogic.parse_call(call)
        if not parsed:
            raise ValueError(f"Invalid auction call: {call}")
        if parsed["type"] == "PASS":
            return "PASS"
        if parsed["type"] == "DOUBLE":
            return "DBL"
        if parsed["type"] == "REDOUBLE":
            return "RDBL"
        return f'{parsed["level"]}{parsed["strain"]}'

    @staticmethod
    def _derive_contract(game, bidding_route):
        for call in bidding_route:
            if not game.make_bid(game.current_bidder, call):
                raise ValueError(f"Illegal auction call: {call}")
        if not game.is_bidding_over:
            return "", game.dealer, False
        return game.contract or "PASSED_OUT", game.declarer or game.dealer, True

    def _refresh_dds_result(self, hands):
        self.dds_trick_table = None
        if not self.dds_wrapper.is_available():
            self._clear_dds_result_matrix()
            return
        pbn_deal = "N:" + " ".join(
            hands[seat] for seat in ("NORTH", "EAST", "SOUTH", "WEST")
        )
        result = self.dds_wrapper.calc_dd_table_pbn(pbn_deal)
        if result is None:
            self._clear_dds_result_matrix()
            return

        tricks = result.get("res_table") if isinstance(result, dict) else None
        if (
            isinstance(tricks, (list, tuple))
            and len(tricks) == 5
            and all(
                isinstance(row, (list, tuple))
                and len(row) == 4
                and all(isinstance(value, int) for value in row)
                for row in tricks
            )
        ):
            self.dds_trick_table = [list(row) for row in tricks]
            self._render_dds_result_matrix()
        else:
            self._clear_dds_result_matrix()

    def _render_dds_result_matrix(self):
        if self.dds_trick_table is None:
            self._clear_dds_matrix_cells()
            return
        contract_mode = self.dds_display_mode == "CONTRACT_OFFSET"
        if contract_mode and self._contract_target_tricks() is None:
            self._clear_dds_matrix_cells()
            return

        for row_index, seat in enumerate(self.DDS_MATRIX_SEATS):
            dds_seat_index = self.DDS_SEATS.index(seat)
            for column_index, strain in enumerate(self.DDS_STRAINS):
                dds_strain_index = self.DDS_STRAINS.index(strain)
                tricks = self.dds_trick_table[dds_strain_index][dds_seat_index]
                if contract_mode:
                    tricks = max(0, tricks - 6)
                text = str(tricks)
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.dds_result_table.setItem(row_index, column_index, item)

    def _clear_dds_result_matrix(self):
        self._clear_dds_matrix_cells()

    def _clear_dds_matrix_cells(self):
        for row in range(self.dds_result_table.rowCount()):
            for column in range(self.dds_result_table.columnCount()):
                item = QTableWidgetItem("")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.dds_result_table.setItem(row, column, item)

    def _contract_target_tricks(self) -> Optional[int]:
        if not self.scenario:
            return None
        parsed_contract = BridgeLogic.parse_call(self.scenario.contract)
        if not parsed_contract or parsed_contract.get("type") != "BID":
            return None
        return parsed_contract["level"] + 6

    def toggle_dds_display_mode(self):
        if self.current_mode == "DEMONSTRATION":
            return
        mode = (
            "CONTRACT_OFFSET"
            if self.dds_display_mode == "TRICKS"
            else "TRICKS"
        )
        self.set_dds_display_mode(mode)

    def set_dds_display_mode(self, mode: str):
        if self.current_mode == "DEMONSTRATION":
            return
        if mode not in self.dds_mode_actions:
            raise ValueError(f"Unsupported DDS display mode: {mode}")
        changed = self.dds_display_mode != mode
        self.dds_display_mode = mode
        self.dds_mode_actions[mode].setChecked(True)
        self._render_dds_result_matrix()
        self._apply_card_dds_scores()
        if changed:
            self.preferences_changed.emit()

    def set_suit_symbol_size(self, size: int):
        if type(size) is not int or not 10 <= size <= 35:
            raise ValueError(f"Unsupported suit symbol size: {size}")
        changed = self.suit_symbol_size != size
        self.suit_symbol_size = size
        if self.suit_symbol_size_slider.value() != size:
            self.suit_symbol_size_slider.setValue(size)
        for hand in self.hand_widgets.values():
            hand.set_suit_symbol_size(size)
        for card_widget in self.findChildren(CardWidget):
            card_widget.set_suit_symbol_size(size)
        if changed:
            self.preferences_changed.emit()

    def _render_hands(self):
        self._stop_robot_animation()
        if not self.game:
            for hand in self.hand_widgets.values():
                hand.set_hand([])
            self._render_played_cards()
            self._apply_view_mode()
            self._refresh_card_dds_results()
            self._update_dds_visibility()
            return

        labels_by_card = {
            label["Card"]: label
            for label in sorted(
                self.labels,
                key=lambda item: item.get("Sequence", 999),
                reverse=True,
            )
        }
        for seat, hand_data in self.game.hands.items():
            cards = [
                f"{suit}{rank}"
                for suit in ("S", "H", "D", "C")
                for rank in hand_data[suit]
            ]
            hand_widget = self.hand_widgets[seat]
            hand_widget.set_hand(cards)
            for card_widget in hand_widget.cards:
                card_label = (
                    None
                    if self.test_playback_active
                    or self.current_mode == "DEMONSTRATION"
                    else labels_by_card.get(card_widget.card_code)
                )
                card_widget.set_label_color(
                    card_label.get("Color", "NONE")
                    if card_label
                    else "NONE"
                )
                card_widget.set_label_sequence(
                    card_label.get("Sequence")
                    if card_label
                    else None
                )
        self._render_played_cards()
        self._apply_view_mode()
        self._refresh_card_dds_results()
        self._update_dds_visibility()

    def _refresh_card_dds_results(self):
        self.dds_card_scores = {}
        if (
            not self.game
            or self.current_mode != "NORMAL"
            or self.view_mode != "ANALYSIS"
            or not self.game.current_player
            or not self.dds_wrapper.is_available()
        ):
            self._apply_card_dds_scores()
            return

        player = self.game.current_player
        legal_cards = set(self.game.get_legal_cards(player))
        if not legal_cards:
            self._apply_card_dds_scores()
            return
        for card in legal_cards:
            tricks = self._solve_dds_after_card(player, card)
            if tricks is not None:
                self.dds_card_scores[card] = tricks
        self._apply_card_dds_scores()

    def _solve_dds_after_card(self, player: str, card: str) -> Optional[int]:
        trial_game = copy.deepcopy(self.game)
        player_side = self.PARTNERS[player]
        previous_side_tricks = sum(
            trial_game.tricks_won[seat] for seat in player_side
        )
        if not trial_game.play_card(player, card):
            return None

        played_side_tricks = (
            sum(trial_game.tricks_won[seat] for seat in player_side)
            - previous_side_tricks
        )
        remaining_tricks = 13 - len(trial_game.completed_tricks)
        if not trial_game.current_player:
            return played_side_tricks

        trick_suits = tuple(
            SUITS.index(played_card[0])
            for _, played_card in trial_game.current_trick
        )
        trick_ranks = tuple(
            RANKS.index(played_card[1:]) + 2
            for _, played_card in trial_game.current_trick
        )
        trick_leader = (
            trial_game.current_trick[0][0]
            if trial_game.current_trick
            else trial_game.current_player
        )
        result = self.dds_wrapper.solve_board_pbn(
            trial_game.get_current_pbn_deal(),
            trump=self.DDS_TRUMPS[trial_game.trump_suit or "NT"],
            first=self.DDS_SEATS.index(trick_leader),
            current_trick_suit=trick_suits + (0,) * (3 - len(trick_suits)),
            current_trick_rank=trick_ranks + (0,) * (3 - len(trick_ranks)),
            target=-1,
            solutions=3,
            mode=0,
        )
        dds_tricks = self._parse_dds_best_score(result)
        if dds_tricks is None:
            return None

        future_side_tricks = (
            dds_tricks
            if trial_game.current_player in player_side
            else remaining_tricks - dds_tricks
        )
        return previous_side_tricks + played_side_tricks + future_side_tricks

    @staticmethod
    def _parse_dds_best_score(result: Any) -> Optional[int]:
        if not isinstance(result, dict):
            return None
        card_count = result.get("cards")
        scores = result.get("score")
        if (
            not isinstance(card_count, int)
            or not isinstance(scores, (list, tuple))
        ):
            return None

        valid_scores = [
            score
            for score in scores[:card_count]
            if isinstance(score, int)
        ]
        return max(valid_scores) if valid_scores else None

    def _apply_card_dds_scores(self):
        for hand in self.hand_widgets.values():
            for card_widget in hand.cards:
                card_widget.set_dds_tricks(None)
        if (
            not self.game
            or self.current_mode != "NORMAL"
            or self.view_mode != "ANALYSIS"
            or not self.game.current_player
        ):
            return

        player = self.game.current_player
        for card_widget in self.hand_widgets[player].cards:
            tricks = self.dds_card_scores.get(card_widget.card_code)
            if tricks is None:
                continue
            display_value = self._format_card_dds_value(player, tricks)
            if display_value is not None:
                card_widget.set_dds_tricks(display_value)

    def _format_card_dds_value(self, player: str, tricks: int) -> Optional[int]:
        if self.dds_display_mode == "TRICKS":
            return tricks
        contract_target = self._contract_target_tricks()
        if contract_target is None or not self.game or not self.game.declarer:
            return None

        declarer_side = self.PARTNERS[self.game.declarer]
        declarer_tricks = (
            tricks if player in declarer_side else 13 - tricks
        )
        return declarer_tricks - contract_target

    def _render_played_cards(self):
        for widget in self._played_card_widget_pool.values():
            self.played_cards_grid.removeWidget(widget)
            widget.hide()
        self.played_card_widgets = {}
        if not self.game:
            return

        trick = self.game.current_trick
        if not trick and self.game.completed_tricks:
            trick = self.game.completed_tricks[-1]

        positions = {
            0: (2, 1),
            1: (1, 0),
            2: (0, 1),
            3: (1, 2),
        }
        perspective_index = self.SEATS_CLOCKWISE.index(self.perspective)
        for seat, card_code in trick:
            relative_position = (
                self.SEATS_CLOCKWISE.index(seat) - perspective_index
            ) % 4
            card_widget = self._played_card_widget_pool.get(seat)
            if card_widget is None or card_widget.card_width != self.card_size:
                if card_widget is not None:
                    card_widget.deleteLater()
                card_widget = CardWidget(
                    card_code,
                    self.played_card_area,
                    card_width=self.card_size,
                    suit_symbol_size=self.suit_symbol_size,
                )
                self._played_card_widget_pool[seat] = card_widget
            else:
                card_widget.set_card_code(card_code)
            self.played_cards_grid.addWidget(
                card_widget,
                *positions[relative_position],
                alignment=Qt.AlignmentFlag.AlignCenter,
            )
            self.played_card_widgets[seat] = card_widget
            card_widget.show()

    def _apply_view_mode(self):
        conceal_opponents = (
            self.current_mode == "DEMONSTRATION"
            and self.view_mode == "HIDDEN"
        )
        hidden_seats = set()
        if conceal_opponents and self.game and self.game.declarer:
            declarer_side = self.PARTNERS[self.game.declarer]
            if self.current_side in declarer_side:
                visible_seats = declarer_side
            else:
                dummy = next(
                    seat for seat in declarer_side
                    if seat != self.game.declarer
                )
                first_trick = (
                    self.game.completed_tricks[0]
                    if self.game.completed_tricks
                    else self.game.current_trick
                )
                dummy_revealed = any(
                    seat == self.current_side for seat, _ in first_trick
                )
                visible_seats = {self.current_side}
                if dummy_revealed:
                    visible_seats.add(dummy)
            hidden_seats = set(self.SEATS_CLOCKWISE) - visible_seats

        for seat, hand in self.hand_widgets.items():
            hidden = bool(self.game and seat in hidden_seats)
            hand.setVisible(True)
            hand.set_hidden(hidden)
            self.seat_labels[seat].setVisible(True)

    def _update_dds_visibility(self):
        dds_enabled = (
            self.current_mode == "NORMAL"
            and self.view_mode == "ANALYSIS"
            and not self.lockdown_mode
        )
        self.dds_slot.setCurrentIndex(
            0 if dds_enabled and not self.dds_matrix_hidden else 1
        )
        self.dds_visibility_action.setChecked(not self.dds_matrix_hidden)
        self._apply_card_dds_scores()
        if hasattr(self, "footer_controls"):
            self._position_overlay_widgets()

    def set_dds_matrix_visible(self, visible: bool):
        changed = self.dds_matrix_hidden == visible
        self.dds_matrix_hidden = not visible
        self._update_dds_visibility()
        if changed:
            self.preferences_changed.emit()

    def _place_seats(self):
        while self.table_grid.count():
            self.table_grid.takeAt(0)

        positions = {
            0: (2, 0, 1, 3),
            1: (1, 0, 1, 1),
            2: (0, 0, 1, 3),
            3: (1, 2, 1, 1),
        }
        bottom_index = self.SEATS_CLOCKWISE.index(self.perspective)
        for seat, hand in self.hand_widgets.items():
            relative_position = (
                self.SEATS_CLOCKWISE.index(seat) - bottom_index
            ) % 4
            hand.set_horizontal(relative_position in {0, 2})
            side_label_top_margin = (
                18 if relative_position in {1, 3} else 2
            )
            self.seat_layouts[seat].setContentsMargins(
                2,
                side_label_top_margin,
                2,
                2,
            )
            self.table_grid.addWidget(
                self.seat_containers[seat],
                *positions[relative_position],
            )
        self.table_grid.addWidget(
            self.trick_area,
            1,
            1,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )

    def open_settings(self):
        if self.scenario is None:
            self.center_info.setText("Create or load a scenario before changing settings.")
            return
        if self.test_playback_active:
            dialog = BiddingBoxDialog(
                self.bidding_route.copy(),
                dealer=self.configuration.dealer,
                parent=self,
                read_only=True,
                route_only=True,
            )
            self.language_controller.install(dialog)
            exec_and_delete(dialog)
            return
        dialog = BiddingBoxDialog(
            self.bidding_route.copy(),
            dealer=self.configuration.dealer,
            parent=self,
        )
        self.language_controller.install(dialog)
        if exec_and_delete(dialog):
            saved_mode = self.current_mode
            saved_rule = self.rule_mode
            saved_side = self.current_side
            self.bidding_route = dialog.bidding_history.copy()
            self.scenario.bidding_route = " ".join(self.bidding_route)
            self.scenario.risk_status = dialog.risk_status
            self.load_board(
                self.board,
                self.configuration,
                self.scenario,
                self.labels,
                force_robot=(
                    self.lockdown_mode
                    and saved_mode == "DEMONSTRATION"
                    and saved_rule == "LABEL"
                ),
                test_playback=self.test_playback_active,
            )
            if self.lockdown_mode and saved_mode == "DEMONSTRATION":
                self.current_side = saved_side
                self.rule_mode = saved_rule
                self.view_mode = "HIDDEN"
                self._apply_view_mode()
                self.set_mode("DEMONSTRATION")
                self._update_lockdown_controls()

    def rotate_perspective(self):
        if self.current_mode == "DEMONSTRATION":
            return
        perspectives = ["SOUTH", "WEST", "NORTH", "EAST"]
        current_index = perspectives.index(self.perspective)
        self.perspective = perspectives[(current_index + 1) % len(perspectives)]
        self._place_seats()
        self._render_hands()
        self._update_table_canvas_size()
        self.preferences_changed.emit()

    def set_card_size(self, size: int | str):
        sizes = {"STANDARD": 44, "LARGE": 50}
        card_width = sizes.get(size.upper(), None) if isinstance(size, str) else size
        if not isinstance(card_width, int) or not 35 <= card_width <= 50:
            raise ValueError(f"Unsupported card size: {size}")
        changed = self.card_size != card_width
        self.card_size = card_width
        if self.card_size_slider.value() != card_width:
            self.card_size_slider.setValue(card_width)
        for hand in self.hand_widgets.values():
            hand.set_card_size(card_width)
        self._render_hands()
        self._update_table_canvas_size()
        self._update_scenario_controls()
        if changed:
            self.preferences_changed.emit()

    def set_robot_speed(self, delay_ms: int):
        if not 300 <= delay_ms <= 3000:
            raise ValueError(f"Unsupported robot delay: {delay_ms}")
        changed = self.robot_move_delay_ms != delay_ms
        self.robot_move_delay_ms = delay_ms
        if self.robot_speed_slider.value() != delay_ms:
            self.robot_speed_slider.setValue(delay_ms)
        if self.robot_timer.isActive():
            self.robot_timer.start(delay_ms)
        if changed:
            self.preferences_changed.emit()

    def _set_sound_volume(self, volume: int):
        scaled_volume = volume / 100
        self.robot_card_sound.setVolume(scaled_volume)

    def set_sound_volume(self, volume: int):
        if type(volume) is not int or not 0 <= volume <= 100:
            raise ValueError(f"Unsupported sound volume: {volume}")
        changed = self.sound_volume_percent != volume
        self.sound_volume_percent = volume
        self._set_sound_volume(volume)
        if self.sound_volume_slider.value() != volume:
            self.sound_volume_slider.setValue(volume)
        if changed:
            self.preferences_changed.emit()

    def _set_robot_card_sound_source(self, choice: str):
        filename = self.robot_sound_paths.get(choice)
        if filename is None:
            raise ValueError(f"Unsupported robot sound: {choice}")
        sound_path = (
            Path(__file__).resolve().parents[3]
            / "assets"
            / "sounds"
            / filename
        )
        if not sound_path.is_file():
            raise FileNotFoundError(f"Robot sound file not found: {sound_path}")
        self.robot_card_sound.stop()
        self.robot_card_sound.setSource(QUrl.fromLocalFile(str(sound_path)))

    def set_robot_card_sound_choice(self, choice: str):
        if choice not in {"OFF", *self.robot_sound_paths}:
            raise ValueError(f"Unsupported robot sound: {choice}")
        changed = self.robot_card_sound_choice != choice
        self.robot_card_sound_choice = choice
        self.robot_card_sound_enabled = choice != "OFF"
        self.robot_card_sound_action.setChecked(self.robot_card_sound_enabled)
        if self.robot_card_sound_enabled:
            self._set_robot_card_sound_source(choice)
        else:
            self.robot_card_sound.stop()
        if changed:
            self.preferences_changed.emit()

    def _apply_test_playback_preferences(self):
        self.set_card_size(self.TEST_CARD_SIZE_PX)
        self.set_robot_speed(self.TEST_ROBOT_MOVE_DELAY_MS)
        self.set_robot_card_sound_choice("CLASSIC")
        self.set_sound_volume(self.TEST_SOUND_VOLUME_PERCENT)

    def _apply_test_playback_appearance(self):
        if self.test_playback_active == self._test_playback_appearance_active:
            return
        self._test_playback_appearance_active = self.test_playback_active
        if self.test_playback_active:
            center_font = QFont(self.center_info.font())
            center_font.setPixelSize(24)
            self.center_info.setFont(center_font)
            bidding_font = QFont(self.btn_bidding.font())
            bidding_font.setPixelSize(18)
            self.btn_bidding.setFont(bidding_font)
            self.center_info.setMinimumHeight(120)
            self.center_info.setMaximumWidth(680)
            self.info_overlay.setFixedHeight(132)
            self.info_overlay.layout().setAlignment(
                self.center_info,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            )
            self.btn_bidding.setMinimumHeight(48)
        else:
            self.center_info.setFont(QFont())
            self.btn_bidding.setFont(QFont())
            self.center_info.setMinimumHeight(66)
            self.center_info.setMaximumWidth(460)
            self.info_overlay.setFixedHeight(72)
            self.info_overlay.layout().setAlignment(
                self.center_info,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            )
            self.btn_bidding.setMinimumHeight(0)
        self._position_overlay_widgets()

    def set_robot_card_sound_enabled(self, enabled: bool):
        self.set_robot_card_sound_choice(
            self.robot_card_sound_choice
            if enabled and self.robot_card_sound_choice != "OFF"
            else "CLASSIC"
            if enabled
            else "OFF"
        )

    def toggle_view_mode(self):
        mode = "HIDDEN" if self.view_mode == "ANALYSIS" else "ANALYSIS"
        self.set_view_mode(mode)

    def set_view_mode(self, mode: str):
        if mode not in self.view_actions:
            raise ValueError(f"Unsupported view mode: {mode}")
        changed = self.preferred_view_mode != mode
        self.preferred_view_mode = mode
        self.view_mode = mode
        self.view_actions[mode].setChecked(True)
        self._apply_view_mode()
        self._refresh_card_dds_results()
        self._update_dds_visibility()
        self._update_scenario_controls()
        if changed:
            self.preferences_changed.emit()

    def show_description(self):
        if self.scenario is None:
            return
        language = self.language_controller.language
        information = self.scenario.information or translate_text(
            "No additional scenario information is available.",
            language,
        )
        dialog = TestScenarioDialog(
            "Scenario description",
            (
                "Scenario information"
                if self.test_playback_active
                else self.scenario.name or "Scenario information"
            ),
            information=information,
            action_text="Close",
            eyebrow="SCENARIO INFORMATION",
            language=language,
            parent=self,
        )
        self.language_controller.install(dialog)
        exec_and_delete(dialog)

    def show_label_instructions(self):
        if self.lockdown_mode:
            return
        dialog = LabelDefinitionDialog(
            self.label_jobs,
            self.language_controller.language,
            parent=self,
        )
        self.language_controller.install(dialog)
        exec_and_delete(dialog)

    def toggle_mode(self):
        target_mode = (
            "NORMAL"
            if self.current_mode == "DEMONSTRATION"
            else "DEMONSTRATION"
        )
        if self.set_mode(target_mode):
            self.mode_changed.emit(target_mode)

    def toggle_rule_mode(self):
        if self.scenario is None:
            return
        mode = "TARGET" if self.rule_mode == "LABEL" else "LABEL"
        self.set_rule_mode(mode)

    def set_rule_mode(self, mode: str):
        if self.scenario is None:
            return
        if self.current_mode == "DEMONSTRATION":
            self.set_mode("NORMAL")
            self.mode_changed.emit("NORMAL")
        self.rule_mode = mode
        self.scenario.is_targeted = int(self.rule_mode == "TARGET")
        self.rule_actions[mode].setChecked(True)
        self._reset_play_state()
        self._update_scenario_controls()

    def record_completed_play(self):
        if (
            self.scenario is None
            or self.game is None
            or self.current_mode != "NORMAL"
            or self.view_mode != "ANALYSIS"
            or self.lockdown_mode
            or self.test_playback_active
            or not self._auction_is_playable()
            or not self._is_board_complete()
        ):
            return False

        sequence = [
            card
            for trick in self.game.completed_tricks
            for _player, card in trick
        ]
        if len(sequence) != 52 or len(set(sequence)) != 52:
            self.center_info.setText(
                "The completed play does not contain 52 unique cards."
            )
            return False

        self.target_sequence = sequence
        self.scenario.targeted_sequence = json.dumps(sequence)
        self.scenario.is_targeted = 1
        self.rule_mode = "TARGET"
        self.rule_actions["TARGET"].setChecked(True)
        self.scenario_changed.emit()
        self.center_info.setText("Target sequence recorded: 52 cards.")
        self._update_navigation()
        self._update_scenario_controls()
        return True

    def on_card_context_requested(self, player: str, card: str):
        if (
            self.scenario is None
            or self.view_mode != "ANALYSIS"
            or self.rule_mode != "LABEL"
            or self.current_mode != "NORMAL"
        ):
            return
        existing = next(
            (label for label in self.labels if label["Card"] == card),
            None,
        )
        current_color = existing["Color"] if existing else "RED"
        sequence_counts = {
            color: (
                existing.get("Sequence", 1)
                if existing and color == current_color
                else 1 + sum(
                    label.get("Color") == color and label.get("Card") != card
                    for label in self.labels
                )
            )
            for color in CardWidget.COLOR_MAP
            if color != "NONE"
        }
        current_sequence = (
            existing.get("Sequence", 1)
            if existing
            else sequence_counts[current_color]
        )
        dialog = LabelColorDialog(
            card,
            current_color,
            self,
            current_sequence=current_sequence,
            sequence_counts=sequence_counts,
        )
        self.language_controller.install(dialog)
        if not exec_and_delete(dialog):
            return
        self._set_card_label(
            card,
            dialog.selected_color,
            dialog.selected_sequence,
        )
        self._render_hands()
        self._update_scenario_controls()

    def _set_card_label(self, card: str, color: str, sequence: int):
        existing_index = next(
            (
                index for index, label in enumerate(self.labels)
                if label.get("Card") == card
            ),
            len(self.labels),
        )
        existing = (
            self.labels[existing_index]
            if existing_index < len(self.labels)
            else None
        )
        remaining = [
            label for label in self.labels
            if label.get("Card") != card
        ]
        old_color = existing.get("Color") if existing else None
        if old_color and old_color != color:
            old_color_labels = sorted(
                (
                    label for label in remaining
                    if label.get("Color") == old_color
                ),
                key=lambda label: label.get("Sequence", 0),
            )
            for index, label in enumerate(old_color_labels, start=1):
                label["Sequence"] = index

        if color == "NONE":
            self.labels = remaining
            return

        same_color = sorted(
            (
                label for label in remaining
                if label.get("Color") == color
            ),
            key=lambda label: label.get("Sequence", 0),
        )
        insertion_index = min(max(int(sequence) - 1, 0), len(same_color))
        new_label = {
            "Sequence": insertion_index + 1,
            "Color": color,
            "Card": card,
        }
        same_color.insert(
            insertion_index,
            new_label,
        )
        for index, label in enumerate(same_color, start=1):
            label["Sequence"] = index
        self.labels = remaining
        self.labels.insert(min(existing_index, len(self.labels)), new_label)

    def _reset_play_state(self):
        if not self.board or not self.configuration or not self.scenario:
            return
        self._stop_robot_playback()
        self.robot = None
        hands = {
            seat: getattr(self.board, attribute)
            for seat, attribute in self.SEAT_PBN_ATTRIBUTES.items()
        }
        game = BridgeGameEngine(
            hands,
            dealer=self.configuration.dealer,
            vulnerability=self.configuration.vulnerability,
        )
        contract, declarer, auction_complete = self._derive_contract(
            game,
            self.bidding_route,
        )
        self.scenario.contract = contract
        self.scenario.declarer = declarer
        if auction_complete and contract != "PASSED_OUT":
            game.start_play(contract, declarer, self.scenario.risk_status)
        self.game = game
        self.demonstration_result_shown = False
        self._completion_emitted = False
        self.target_index = 0
        self.move_history.clear()
        self.robot_error_message = None
        self.robot = (
            RobotAgent(
                game,
                self.dds_wrapper,
                color_jobs=self.label_jobs,
            )
            if self.is_scenario_ready()
            and self.rule_mode == "LABEL"
            and contract != "PASSED_OUT"
            else None
        )
        self._render_hands()
        self._update_table_canvas_size()
        self._update_navigation()
        self._update_center_info()

    def _auction_is_playable(self):
        return bool(
            self.scenario
            and self.game
            and self.game.current_player
            and self.scenario.contract
            and self.scenario.contract.upper() != "PASSED_OUT"
        )

    def start_demonstration(self):
        if not self.set_mode("DEMONSTRATION"):
            return False
        self.mode_changed.emit("DEMONSTRATION")
        return True

    def toggle_demonstration(self):
        if self.current_mode == "DEMONSTRATION":
            return self.end_demonstration()
        return self.start_demonstration()

    def end_demonstration(self):
        if self.current_mode != "DEMONSTRATION":
            return False
        if not self.set_mode("NORMAL"):
            return False
        self.mode_changed.emit("NORMAL")
        return True

    def select_side(self):
        if self.current_mode == "DEMONSTRATION":
            return
        sides = ["SOUTH", "WEST", "NORTH", "EAST"]
        current_index = sides.index(self.current_side)
        self.current_side = sides[(current_index + 1) % len(sides)]
        if (
            self.current_mode == "DEMONSTRATION"
            and self.scenario
            and self.rule_mode == "LABEL"
        ):
            self._advance_robots()
            self._render_hands()
        self._apply_view_mode()
        self._update_center_info()
        self.preferences_changed.emit()

    def set_mode(self, mode: str):
        entering_demonstration = (
            mode == "DEMONSTRATION"
            and self.current_mode != "DEMONSTRATION"
        )
        if mode != "DEMONSTRATION":
            self._stop_robot_playback()
        if mode == "DEMONSTRATION" and (
            not self.is_scenario_ready()
            or self.scenario.contract.upper() == "PASSED_OUT"
        ):
            self.center_info.setText(
                "Complete the scenario setup before demonstration."
            )
            self._update_scenario_controls()
            return False
        if entering_demonstration:
            self._reset_play_state()
        self.current_mode = mode
        if mode == "DEMONSTRATION":
            self.demonstration_result_shown = False
        if entering_demonstration:
            self._advance_robots()
        self._render_hands()
        self._apply_view_mode()
        self._update_dds_visibility()
        self._update_scenario_controls()
        self._update_center_info()
        return True

    def on_card_selected(self, player: str, card: str):
        if not self.game or not self.scenario:
            self.center_info.setText("Select a playable scenario before playing cards.")
            return
        if self.current_mode not in {"NORMAL", "DEMONSTRATION"}:
            self.center_info.setText("Card selection is not available in this mode.")
            return
        if self.current_mode == "NORMAL" and not self._auction_is_playable():
            self.center_info.setText(
                "Complete the auction in Bidding before playing cards."
            )
            return
        if (
            self.current_mode == "DEMONSTRATION"
            and not self.is_scenario_ready()
        ):
            self.center_info.setText(
                "Complete the scenario setup before demonstration."
            )
            return
        if (
            self.current_mode == "DEMONSTRATION"
            and self.rule_mode == "TARGET"
            and (
                self.target_index >= len(self.target_sequence)
                or card != self.target_sequence[self.target_index]
            )
        ):
            expected = (
                self.target_sequence[self.target_index]
                if self.target_index < len(self.target_sequence)
                else "no card"
            )
            self.center_info.setText(
                f"The recorded sequence requires {expected}."
            )
            return
        human_seats = self._human_controlled_seats()
        if player != self.game.current_player:
            self.center_info.setText(
                f"It is {self.game.current_player or 'no player'}'s turn."
            )
            return
        if (
            self.current_mode == "DEMONSTRATION"
            and player not in human_seats
        ):
            self.center_info.setText(
                f"The robot controls {player} during this demonstration."
            )
            return
        if not self._play_card(player, card):
            self.center_info.setText(f"{card} is not a legal card for {player}.")
            return
        if (
            self.current_mode == "DEMONSTRATION"
            and self.rule_mode == "TARGET"
        ):
            self.target_index += 1
        self._advance_robots()
        self._render_hands()
        self._update_navigation()
        self._update_center_info()

    def _human_controlled_seats(self) -> set[str]:
        if self.current_mode == "NORMAL":
            return set(self.SEATS_CLOCKWISE)
        if (
            self.current_mode == "DEMONSTRATION"
            and self.game
            and self.game.declarer
            and self.current_side in self.PARTNERS[self.game.declarer]
        ):
            return self.PARTNERS[self.current_side]
        return {self.current_side}

    def _play_card(self, player: str, card: str):
        if not self.game:
            return False
        if card not in self.game.get_legal_cards(player):
            return False
        self.move_history.append(
            (
                copy.deepcopy(self.game),
                self.target_index,
                len(self.target_sequence),
            )
        )
        if len(self.move_history) > 64:
            self.move_history.pop(0)
        if not self.game.play_card(player, card):
            self.move_history.pop()
            return False
        if self._is_board_complete() and not self._completion_emitted:
            self._completion_emitted = True
            QTimer.singleShot(0, self.scenario_completed.emit)
        return True

    def _advance_robots(self):
        if not self._robots_should_play():
            return
        self.robot_error_message = None
        if not self.robot_timer.isActive():
            self.robot_timer.start(self.robot_move_delay_ms)

    def _robots_should_play(self) -> bool:
        if (
            self.current_mode != "DEMONSTRATION"
            or not self.game
            or not self.game.current_player
            or self._is_board_complete()
        ):
            return False
        if self.rule_mode == "TARGET":
            return bool(
                self.target_index < len(self.target_sequence)
                and self.game.current_player
                not in self._human_controlled_seats()
            )
        return bool(
            self.robot
            and self.game.current_player not in self._human_controlled_seats()
        )

    def _play_next_robot_move(self):
        if not self._robots_should_play():
            return
        if self.rule_mode == "TARGET":
            self.play_next_target_card(animate=True)
            return

        player = self.game.current_player
        card = self.robot.select_move(
            player,
            self.labels,
            self.game.get_current_pbn_deal(),
        )
        if card is None or card not in self.game.get_legal_cards(player):
            self.robot_error_message = (
                f"The robot could not choose a legal move for {player}. "
                "Check DDS availability or scenario labels."
            )
            self._update_center_info()
            return

        source_widget = next(
            (
                card_widget
                for card_widget in self.hand_widgets[player].cards
                if card_widget.card_code == card
            ),
            None,
        )
        source_rect = None
        if source_widget is not None:
            source_rect = QRect(
                source_widget.mapTo(self, QPoint(0, 0)),
                source_widget.size(),
            )

        if not self._play_card(player, card):
            self.robot_error_message = (
                f"The robot could not play {card} for {player}."
            )
            self._update_center_info()
            return

        self._render_hands()
        self._play_robot_card_sound()
        destination_widget = self.played_card_widgets.get(player)
        if source_rect is not None and destination_widget is not None:
            self._animate_robot_card(card, source_rect, destination_widget)
        self._update_navigation()
        self._update_center_info()

        if self._robots_should_play():
            self.robot_timer.start(self.robot_move_delay_ms)

    def _play_robot_card_sound(self):
        if self.robot_card_sound_enabled:
            self.robot_card_sound.play()

    def _animate_robot_card(
        self,
        card: str,
        source_rect: QRect,
        destination_widget: QWidget,
    ):
        self.trick_grid.activate()
        self.played_cards_grid.activate()
        destination_position = destination_widget.mapTo(
            self,
            destination_widget.rect().center(),
        )
        overlay = CardWidget(
            card,
            self,
            card_width=self.card_size,
            suit_symbol_size=self.suit_symbol_size,
        )
        end_rect = QRect(
            destination_position.x() - overlay.width() // 2,
            destination_position.y() - overlay.height() // 2,
            overlay.width(),
            overlay.height(),
        )
        destination_widget.setVisible(False)
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        overlay.setGeometry(source_rect)
        overlay.show()
        overlay.raise_()

        animation = QPropertyAnimation(overlay, b"geometry", self)
        animation.setDuration(self.ROBOT_CARD_ANIMATION_MS)
        animation.setStartValue(source_rect)
        animation.setEndValue(end_rect)
        animation.finished.connect(
            lambda animated_card=overlay, current_animation=animation,
            destination=destination_widget: self._finish_robot_animation(
                animated_card,
                current_animation,
                destination,
            )
        )
        self.robot_animation = animation
        self.robot_animation_destination = destination_widget
        animation.start()

    def _finish_robot_animation(
        self,
        overlay: QWidget,
        animation: QPropertyAnimation,
        destination: QWidget,
    ):
        destination.setVisible(True)
        overlay.deleteLater()
        animation.deleteLater()
        if self.robot_animation is animation:
            self.robot_animation = None
            self.robot_animation_destination = None

    def _stop_robot_animation(self):
        if self.robot_animation is None:
            return
        animation = self.robot_animation
        animation.stop()
        animated_card = animation.targetObject()
        destination = self.robot_animation_destination
        if destination is not None:
            destination.setVisible(True)
        if isinstance(animated_card, QWidget):
            animated_card.deleteLater()
        animation.deleteLater()
        self.robot_animation = None
        self.robot_animation_destination = None

    def _stop_robot_playback(self):
        self.robot_timer.stop()
        self._stop_robot_animation()

    def play_next_target_card(self, animate: bool = False):
        if (
            self.current_mode not in {"NORMAL", "DEMONSTRATION"}
            or not self.scenario
            or self.rule_mode != "TARGET"
            or not self.game
        ):
            self.center_info.setText(
                "Next move is available only for a target-rule scenario."
            )
            return
        if self.target_index >= len(self.target_sequence):
            self.center_info.setText("The saved target sequence is complete.")
            return
        player = self.game.current_player
        card = self.target_sequence[self.target_index]
        if player is None or card not in self.game.get_legal_cards(player):
            self.center_info.setText(
                f"Target card {card} is not legal for {player or 'the current position'}."
            )
            return
        source_rect = None
        if animate:
            source_widget = next(
                (
                    card_widget
                    for card_widget in self.hand_widgets[player].cards
                    if card_widget.card_code == card
                ),
                None,
            )
            if source_widget is not None:
                source_rect = QRect(
                    source_widget.mapTo(self, QPoint(0, 0)),
                    source_widget.size(),
                )

        if not self._play_card(player, card):
            self.center_info.setText(f"Target card {card} could not be played.")
            return
        self.target_index += 1
        self._render_hands()
        if animate:
            self._play_robot_card_sound()
            destination = self.played_card_widgets.get(player)
            if source_rect is not None and destination is not None:
                self._animate_robot_card(card, source_rect, destination)
        self._update_navigation()
        self._update_center_info()
        if self._robots_should_play() and not self.robot_timer.isActive():
            self.robot_timer.start(self.robot_move_delay_ms)
        if (
            self.target_index >= len(self.target_sequence)
            and not self._completion_emitted
        ):
            self._completion_emitted = True
            self.scenario_completed.emit()

    def play_previous_target_card(self):
        self._restore_previous_move()

    def play_previous_move(self):
        if (
            self.current_mode not in {"NORMAL", "DEMONSTRATION"}
            or not self.move_history
        ):
            return
        self._stop_robot_playback()
        self._restore_previous_move()
        self._advance_robots()

    def reset_moves(self):
        if (
            self.current_mode not in {"NORMAL", "DEMONSTRATION"}
        ):
            return
        self._stop_robot_playback()
        while self.move_history:
            self.game, self.target_index, sequence_length = self.move_history.pop()
            if self.rule_mode == "TARGET":
                self.target_sequence = self.target_sequence[:sequence_length]
        if self.scenario and self.rule_mode == "TARGET":
            self.scenario.targeted_sequence = json.dumps(self.target_sequence)
        self.demonstration_result_shown = False
        self.robot_error_message = None
        self._render_hands()
        self._update_navigation()
        self._update_center_info()
        self._advance_robots()

    def _restore_previous_move(self):
        if not self.move_history:
            return
        self.game, self.target_index, sequence_length = self.move_history.pop()
        if self.rule_mode == "TARGET":
            self.target_sequence = self.target_sequence[:sequence_length]
        if self.scenario and self.rule_mode == "TARGET":
            self.scenario.targeted_sequence = json.dumps(self.target_sequence)
        self._render_hands()
        self._update_navigation()
        self._update_center_info()

    def play_next_move(self):
        if self.rule_mode == "TARGET":
            self.play_next_target_card()
        elif (
            self.test_playback_active
            and self.current_mode == "DEMONSTRATION"
            and self._robots_should_play()
        ):
            self._stop_robot_playback()
            self._play_next_robot_move()

    def _update_navigation(self):
        can_navigate = self.current_mode == "NORMAL"
        target_moves_available = bool(
            self.scenario
            and self.rule_mode == "TARGET"
            and self.is_scenario_ready()
            and self.scenario.contract.upper() != "PASSED_OUT"
            and self.current_mode in {"NORMAL", "DEMONSTRATION"}
        )
        can_record = bool(
            self.scenario
            and self.current_mode == "NORMAL"
            and self.view_mode == "ANALYSIS"
            and not self.lockdown_mode
            and not self.test_playback_active
            and self._auction_is_playable()
            and self._is_board_complete()
        )
        show_record_button = bool(
            self.board
            and self.current_mode == "NORMAL"
            and self.view_mode == "ANALYSIS"
            and not self.lockdown_mode
            and not self.test_playback_active
        ) or (self.current_mode == "DEMONSTRATION" and not self.lockdown_mode)
        self.btn_record.setVisible(show_record_button)
        self.btn_record.setEnabled(can_record)
        self.btn_record.setToolTip(
            ""
            if can_record
            else (
                "Load or create a scenario before recording a target."
                if self.scenario is None
                else "Play all 52 cards in Analysis before recording a target."
            )
        )
        self.btn_prev.setEnabled(can_navigate and bool(self.move_history))
        self.btn_reset.setEnabled(can_navigate and bool(self.move_history))
        self.btn_next.setEnabled(
            target_moves_available
            and (
                can_navigate
                or (
                    self.current_mode == "DEMONSTRATION"
                    and self.rule_mode == "TARGET"
                )
            )
            and self.target_index < len(self.target_sequence)
        )
        if hasattr(self, "footer_controls"):
            self.navigation_controls.setVisible(
                not self.test_playback_active
            )
            self._position_overlay_widgets()

    def is_scenario_ready(self) -> bool:
        return self._scenario_is_ready(
            self.scenario,
            self.bidding_route,
            self.target_sequence,
            self.labels,
        )

    @staticmethod
    def _scenario_is_ready(
        scenario,
        bidding_route,
        target_sequence,
        _labels,
    ) -> bool:
        if scenario is None:
            return False
        contract = scenario.contract.strip().upper()
        if contract != "PASSED_OUT":
            parsed_contract = BridgeLogic.parse_call(contract)
            if not parsed_contract or parsed_contract.get("type") != "BID":
                return False

        history = []
        for call in bidding_route:
            if not BridgeLogic.is_legal_call(call, history):
                return False
            history.append(call)
        auction_complete = (
            len(history) == 4 and all(call in {"PASS", "P"} for call in history)
        ) or (
            len(history) >= 4
            and all(call in {"PASS", "P"} for call in history[-3:])
        )
        if not auction_complete:
            return False
        if contract == "PASSED_OUT":
            return True
        return bool(target_sequence) if scenario.is_targeted else True

    def _update_scenario_controls(self):
        has_scenario = self.scenario is not None
        is_demonstration = self.current_mode == "DEMONSTRATION"
        self.btn_human_seat.setText(
            translate_text(
                f"Human seat: {self.current_side}",
                self.language_controller.language,
            )
        )
        self.btn_human_seat.setVisible(not self.test_playback_active)
        self.btn_human_seat.setEnabled(
            not is_demonstration and not self.lockdown_mode
        )
        self.btn_bidding.setEnabled(
            has_scenario
        )
        can_start = bool(
            has_scenario
            and not self.lockdown_mode
            and self.scenario.contract.upper() != "PASSED_OUT"
            and self.is_scenario_ready()
        )
        self.btn_demonstration.setText("End" if is_demonstration else "Start")
        self.btn_demonstration.setStyleSheet(
            "background-color: #9f3a38; color: white; font-weight: bold;"
            if is_demonstration
            else "background-color: #2e8b57; color: white; font-weight: bold;"
        )
        self.btn_demonstration.setEnabled(
            (is_demonstration or can_start) and not self.lockdown_mode
        )
        self.btn_demonstration.setVisible(not self.lockdown_mode)
        self.dds_visibility_action.setEnabled(
            self.current_mode == "NORMAL"
            and self.view_mode == "ANALYSIS"
            and not self.lockdown_mode
        )
        for action in self.rule_actions.values():
            action.setEnabled(has_scenario and not self.lockdown_mode)
        self.view_actions["ANALYSIS"].setEnabled(not self.lockdown_mode)
        self.view_actions["HIDDEN"].setEnabled(not self.lockdown_mode)
        self.bidding_action.setEnabled(
            has_scenario
        )
        self.description_action.setEnabled(
            has_scenario
            and (not self.lockdown_mode or self.test_playback_active)
            and (not is_demonstration or self.test_playback_active)
        )
        self.rotate_action.setEnabled(
            self.current_mode != "DEMONSTRATION"
            and not self.lockdown_mode
        )
        self.label_action.setEnabled(not self.lockdown_mode)
        self.card_size_slider.setEnabled(
            self.current_mode != "DEMONSTRATION" and not self.lockdown_mode
        )
        self.robot_speed_slider.setEnabled(not self.lockdown_mode)
        self.dds_mode_actions["TRICKS"].setEnabled(
            self.current_mode != "DEMONSTRATION" and not self.lockdown_mode
        )
        self.dds_mode_actions["CONTRACT_OFFSET"].setEnabled(
            self.current_mode != "DEMONSTRATION" and not self.lockdown_mode
        )
        self._update_navigation()

    def _is_board_complete(self) -> bool:
        return bool(
            self.game
            and all(
                not any(cards for cards in hand.values())
                for hand in self.game.hands.values()
            )
        )

    def _demonstration_result(self) -> Optional[str]:
        if not self.game or not self.scenario or not self.game.declarer:
            return None
        contract = BridgeLogic.parse_call(self.scenario.contract)
        if not contract or contract.get("type") != "BID":
            return None

        declarer_tricks = sum(
            self.game.tricks_won[seat]
            for seat in self.PARTNERS[self.game.declarer]
        )
        difference = declarer_tricks - contract["level"] - 6
        risk_status = self.game.risk_status or self.scenario.risk_status
        multiplier = {
            "NONE": "",
            "DOUBLE": "X",
            "REDOUBLE": "XX",
        }.get(risk_status.upper())
        if multiplier is None:
            return None
        result = "=" if difference == 0 else f"{difference:+d}"
        return (
            f"{contract['level']}{contract['strain']}"
            f"{multiplier}{result}"
        )

    def _show_demonstration_result(self):
        if self.demonstration_result_shown:
            return
        result = self._demonstration_result()
        if result is None:
            return
        self.demonstration_result_shown = True
        show_message(
            self,
            "information",
            "Demonstration complete",
            f"Final result: {result}",
        )

    def _update_center_info(self):
        if not self.board:
            self.center_info.setText(
                "Double-click a scenario to display its deal and play signal."
            )
            self._update_scenario_controls()
            return
        if not self.scenario:
            self.center_info.setText(
                "No scenario is loaded. Double-click a scenario to display it."
            )
            self._update_scenario_controls()
            return
        if self.scenario.contract.upper() == "PASSED_OUT":
            self.center_info.setText("Passed out — no card-play demonstration.")
            self._update_scenario_controls()
            return
        if not self._auction_is_playable():
            self.center_info.setText(
                "Use Bidding to enter a complete, legal auction before card play."
            )
            self._update_scenario_controls()
            return
        if not self.is_scenario_ready():
            self.center_info.setText(
                "Play all 52 cards in Analysis and record the target sequence."
            )
            self._update_scenario_controls()
            return

        if self.robot_error_message:
            self.center_info.setText(self.robot_error_message)
            self._update_scenario_controls()
            return

        if self._is_board_complete():
            self.center_info.setText("Play complete.")
            self._update_scenario_controls()
            if self.current_mode == "DEMONSTRATION":
                self._show_demonstration_result()
            return
        elif self.rule_mode == "TARGET":
            self.center_info.setText(
                f"Target play: {self.target_index}/{len(self.target_sequence)}"
                f"\nNext: {self.game.current_player or '—'}"
            )
        else:
            risk_status = (self.scenario.risk_status or "").strip().upper()
            contract_text = self.scenario.contract
            if risk_status != "NONE":
                contract_text = f"{contract_text} {risk_status}"
            self.center_info.setText(
                f"{contract_text}\n"
                f"Declarer: {self.scenario.declarer.title()}\n"
                f"To play: "
                f"{self.game.current_player.title() if self.game.current_player else '—'}"
            )
        self._update_scenario_controls()
