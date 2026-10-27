import sqlite3

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton
)
from PyQt6.QtCore import Qt
from src.database.repository import Repository
from src.ui.i18n import show_message


class LoginDialog(QDialog):
    """Modal administrator login dialog backed by the SQLite repository."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Administrator login")
        self.resize(380, 220)
        self.repo = Repository()
        self.authenticated_admin = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        layout.addWidget(QLabel("<b>请输入管理员凭证以解锁完整权限：</b>"))

        # Username field.
        user_layout = QHBoxLayout()
        user_layout.addWidget(QLabel("用户名:"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入管理员名称 (例如: admin)")
        user_layout.addWidget(self.username_input)
        layout.addLayout(user_layout)

        # Password field.
        pwd_layout = QHBoxLayout()
        pwd_layout.addWidget(QLabel("密 码:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("请输入登录密码")
        pwd_layout.addWidget(self.password_input)
        layout.addLayout(pwd_layout)

        # Action buttons.
        btn_layout = QHBoxLayout()
        self.btn_login = QPushButton("🔓 登录 (Login)")
        self.btn_login.setStyleSheet("background-color: #2980b9; font-weight: bold;")
        self.btn_login.clicked.connect(self.handle_login)

        self.btn_cancel = QPushButton("❌ 取消 (Cancel)")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_login)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)

    def handle_login(self):
        name = self.username_input.text().strip()
        password = self.password_input.text()

        if not name or not password:
            show_message(self, "warning", "警告", "用户名和密码不能为空！")
            return

        try:
            admin = self.repo.authenticate_admin(name, password)
            if admin:
                self.authenticated_admin = admin
                show_message(
                    self,
                    "information",
                    "Login successful",
                    f"Welcome back, administrator [{admin.name}]!\n"
                    "Advanced access is active.",
                )
                self.accept()
            else:
                show_message(
                    self,
                    "warning",
                    "登录失败",
                    "用户名不存在或密码错误，请重新输入！"
                )
        except sqlite3.Error as e:
            show_message(
                self,
                "critical",
                "系统错误",
                f"验证过程中发生异常：\n{str(e)}"
            )