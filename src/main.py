import sys
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Bridge Demonstration Tool")
    palette = app.palette()
    palette.setColor(
        QPalette.ColorRole.PlaceholderText,
        QColor("#b8c2d0"),
    )
    app.setPalette(palette)

    app.setStyleSheet("""
        QMainWindow {
            background-color: #1b1e23;
        }
        QDialog {
            background-color: #1b1e23;
        }
        QWidget {
            color: #f1f5f9;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 13px;
        }
        QLabel {
            color: #f1f5f9;
        }
        QTreeWidget, QListWidget {
            background-color: #242831;
            border: 1px solid #323846;
            border-radius: 4px;
            color: #f1f5f9;
        }
        QTableWidget, QAbstractItemView {
            background-color: #242831;
            alternate-background-color: #2b303a;
            color: #f1f5f9;
            gridline-color: #4b5563;
            selection-background-color: #315a7d;
            selection-color: #ffffff;
        }
        QHeaderView::section {
            background-color: #343b48;
            color: #ffffff;
            border: 1px solid #4b5563;
            padding: 5px;
        }
        QTreeWidget::item:selected, QListWidget::item:selected {
            background-color: #315a7d;
            color: #ffffff;
        }
        QMenu {
            background-color: #242831;
            color: #f1f5f9;
            border: 1px solid #4b5563;
        }
        QMenu::item:selected {
            background-color: #315a7d;
            color: #ffffff;
        }
        QGroupBox {
            color: #f1f5f9;
            border: 1px solid #4b5563;
            margin-top: 8px;
            padding-top: 8px;
        }
        QPushButton {
            background-color: #2d323f;
            border: 1px solid #404756;
            border-radius: 4px;
            padding: 6px 12px;
            color: #ffffff;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #3b4253;
            border-color: #525d73;
        }
        QPushButton:pressed {
            background-color: #1e222a;
        }
        QPushButton:disabled {
            background-color: #252a33;
            border-color: #3a4250;
            color: #b8c2d0;
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
        QListWidget::item {
            padding: 7px 8px;
            min-height: 30px;
        }
        QLineEdit, QTextEdit, QComboBox, QSpinBox {
            background-color: #242831;
            border: 1px solid #323846;
            border-radius: 4px;
            padding: 5px 8px;
            color: #ffffff;
        }
        QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled, QSpinBox:disabled {
            color: #b8c2d0;
        }
        QStatusBar {
            color: #f1f5f9;
        }
        QToolTip {
            background-color: #f8fafc;
            color: #111827;
            border: 1px solid #64748b;
        }
    """)

    window = MainWindow()
    window.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()