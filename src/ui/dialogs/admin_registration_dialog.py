import sqlite3

from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QMessageBox,
    QVBoxLayout,
)

from src.database.repository import Repository
from src.ui.i18n import show_message


class AdminRegistrationDialog(QDialog):
    """Create an administrator account and its initial workspace."""

    MIN_PASSWORD_LENGTH = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Administrator registration")
        self.resize(420, 220)
        self.repo = Repository()
        self.admin_id = None
        self.default_case_id = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.username_input = QLineEdit()
        self.username_input.setMaxLength(64)
        self.username_input.setPlaceholderText("请输入管理员名称")
        form.addRow("管理员名称：", self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("至少 8 个字符")
        form.addRow("密码：", self.password_input)

        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.returnPressed.connect(self.register)
        form.addRow("确认密码：", self.confirm_password_input)
        layout.addLayout(form)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.btn_register = QPushButton("注册")
        self.btn_register.clicked.connect(self.register)
        button_layout.addWidget(self.btn_register)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(self.btn_cancel)
        layout.addLayout(button_layout)

    def register(self):
        name = self.username_input.text().strip()
        password = self.password_input.text()
        confirmation = self.confirm_password_input.text()

        if len(name) < 3:
            show_message(
                self,
                "warning",
                "信息不完整",
                "管理员名称至少需要 3 个字符。",
            )
            return
        if len(password) < self.MIN_PASSWORD_LENGTH:
            show_message(
                self,
                "warning",
                "密码过短",
                f"密码至少需要 {self.MIN_PASSWORD_LENGTH} 个字符。",
            )
            return
        if password != confirmation:
            show_message(
                self,
                "warning",
                "密码不一致",
                "两次输入的密码不一致。",
            )
            return

        try:
            self.admin_id, self.default_case_id = self.repo.register_admin(
                name,
                password,
            )
        except sqlite3.IntegrityError:
            show_message(
                self,
                "warning",
                "名称已存在",
                "该管理员名称已被使用，请选择其他名称。",
            )
            return
        except sqlite3.Error as error:
            show_message(
                self,
                "critical",
                "注册失败",
                f"无法保存管理员账户：{error}",
            )
            return

        show_message(
            self,
            "information",
            "注册成功",
            "管理员账户已创建，并已准备好个人教学资料夹。",
        )
        self.accept()
