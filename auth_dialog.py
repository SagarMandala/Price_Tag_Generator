"""
PyQt6 Dialogs for Application Authentication and Password Management.
Includes LoginDialog (shown on startup) and ChangePasswordDialog (accessible in Admin settings).
"""

import time
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon

from auth_manager import verify_password, set_new_password, has_custom_password, DEFAULT_PASSWORD


class LoginDialog(QDialog):
    """
    Lock screen dialog displayed before main application launch.
    Requires valid password to proceed.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("BIGG Mart - Security Login")
        self.setFixedSize(420, 360)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self.failed_attempts = 0
        self.lockout_timer = None

        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(14)

        # Header Frame / Brand Icon
        header_vbox = QVBoxLayout()
        header_vbox.setSpacing(4)
        header_vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel("🔒")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 38px;")
        header_vbox.addWidget(icon_lbl)

        title_lbl = QLabel("Authentication Required")
        title_lbl.setObjectName("loginTitle")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_vbox.addWidget(title_lbl)

        subtitle_lbl = QLabel("Enter password to launch Price Tag Generator")
        subtitle_lbl.setObjectName("loginSubtitle")
        subtitle_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_vbox.addWidget(subtitle_lbl)

        layout.addLayout(header_vbox)

        # Password Input Card
        input_vbox = QVBoxLayout()
        input_vbox.setSpacing(6)

        pwd_label = QLabel("Password:")
        pwd_label.setObjectName("inputLabel")
        input_vbox.addWidget(pwd_label)

        input_row = QHBoxLayout()
        input_row.setSpacing(6)

        self.pwd_input = QLineEdit()
        self.pwd_input.setObjectName("pwdInput")
        self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_input.setPlaceholderText("Enter password...")
        self.pwd_input.returnPressed.connect(self.attempt_login)
        self.pwd_input.textChanged.connect(self.clear_error)
        input_row.addWidget(self.pwd_input)

        self.toggle_btn = QPushButton("👁️")
        self.toggle_btn.setObjectName("toggleEyeBtn")
        self.toggle_btn.setToolTip("Show / Hide password")
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.setFixedWidth(38)
        self.toggle_btn.setFixedHeight(38)
        self.toggle_btn.clicked.connect(self.toggle_password_visibility)
        input_row.addWidget(self.toggle_btn)

        input_vbox.addLayout(input_row)

        # Status / Error Label
        self.error_lbl = QLabel("")
        self.error_lbl.setObjectName("errorLabel")
        self.error_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_lbl.setWordWrap(True)
        input_vbox.addWidget(self.error_lbl)

        layout.addLayout(input_vbox)

        # Bottom Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.exit_btn = QPushButton("Exit")
        self.exit_btn.setObjectName("secondaryBtn")
        self.exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.exit_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.exit_btn)

        self.login_btn = QPushButton("Unlock Application")
        self.login_btn.setObjectName("primaryBtn")
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.clicked.connect(self.attempt_login)
        btn_row.addWidget(self.login_btn)

        layout.addLayout(btn_row)

        # Subtle Hint regarding default password
        if not has_custom_password():
            hint_lbl = QLabel(f"ℹ️ Initial default password: <b>{DEFAULT_PASSWORD}</b>")
            hint_lbl.setObjectName("hintLabel")
            hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(hint_lbl)

    def toggle_password_visibility(self):
        if self.pwd_input.echoMode() == QLineEdit.EchoMode.Password:
            self.pwd_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_btn.setText("🔒")
        else:
            self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_btn.setText("👁️")

    def clear_error(self):
        if self.error_lbl.text() and not self.error_lbl.text().startswith("Too many"):
            self.error_lbl.setText("")

    def attempt_login(self):
        entered = self.pwd_input.text()
        if not entered:
            self.error_lbl.setText("Please enter your password.")
            self.pwd_input.setFocus()
            return

        if verify_password(entered):
            self.accept()
        else:
            self.failed_attempts += 1
            if self.failed_attempts >= 3:
                self.error_lbl.setText("Incorrect password. Please wait 2 seconds...")
                self.login_btn.setEnabled(False)
                self.pwd_input.setEnabled(False)
                QTimer.singleShot(2000, self.reset_lockout)
            else:
                remaining = 3 - self.failed_attempts
                self.error_lbl.setText(f"Incorrect password. ({remaining} attempts remaining before delay)")
                self.pwd_input.selectAll()
                self.pwd_input.setFocus()

    def reset_lockout(self):
        self.login_btn.setEnabled(True)
        self.pwd_input.setEnabled(True)
        self.error_lbl.setText("Incorrect password. Please try again.")
        self.pwd_input.selectAll()
        self.pwd_input.setFocus()

    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            }
            #loginTitle {
                font-size: 18px;
                font-weight: 700;
                color: #0F172A;
            }
            #loginSubtitle {
                font-size: 12px;
                color: #64748B;
            }
            #inputLabel {
                font-size: 12px;
                font-weight: 600;
                color: #334155;
            }
            #pwdInput {
                background-color: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                color: #1E293B;
                min-height: 20px;
            }
            #pwdInput:focus {
                border: 1px solid #2563EB;
                background-color: #FFFFFF;
            }
            #toggleEyeBtn {
                background-color: #F1F5F9;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                font-size: 14px;
            }
            #toggleEyeBtn:hover {
                background-color: #E2E8F0;
            }
            #errorLabel {
                font-size: 11px;
                font-weight: 600;
                color: #DC2626;
                min-height: 18px;
            }
            #primaryBtn {
                background-color: #059669;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 700;
                padding: 9px 18px;
                border-radius: 6px;
                border: none;
            }
            #primaryBtn:hover {
                background-color: #047857;
            }
            #primaryBtn:disabled {
                background-color: #94A3B8;
            }
            #secondaryBtn {
                background-color: #F1F5F9;
                color: #475569;
                font-size: 13px;
                font-weight: 600;
                padding: 9px 16px;
                border-radius: 6px;
                border: 1px solid #CBD5E1;
            }
            #secondaryBtn:hover {
                background-color: #E2E8F0;
                color: #1E293B;
            }
            #hintLabel {
                font-size: 11px;
                color: #64748B;
                margin-top: 4px;
            }
        """)


class ChangePasswordDialog(QDialog):
    """
    Admin dialog allowing the user to change the application password.
    Requires verification of the current password.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Admin - Change Application Password")
        self.setFixedSize(440, 420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        # Header
        header_vbox = QVBoxLayout()
        header_vbox.setSpacing(2)
        title_lbl = QLabel("🔐 Change Password")
        title_lbl.setObjectName("dialogTitle")
        subtitle_lbl = QLabel("Update the startup password for Price Tag Generator")
        subtitle_lbl.setObjectName("dialogSubtitle")
        header_vbox.addWidget(title_lbl)
        header_vbox.addWidget(subtitle_lbl)
        layout.addLayout(header_vbox)

        # Current Password
        layout.addWidget(QLabel("Current Password:"))
        self.current_input = QLineEdit()
        self.current_input.setObjectName("formInput")
        self.current_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.current_input.setPlaceholderText("Enter current password...")
        layout.addWidget(self.current_input)

        # New Password
        layout.addWidget(QLabel("New Password:"))
        self.new_input = QLineEdit()
        self.new_input.setObjectName("formInput")
        self.new_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_input.setPlaceholderText("Enter new password (min 3 characters)...")
        layout.addWidget(self.new_input)

        # Confirm New Password
        layout.addWidget(QLabel("Confirm New Password:"))
        self.confirm_input = QLineEdit()
        self.confirm_input.setObjectName("formInput")
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input.setPlaceholderText("Re-type new password...")
        layout.addWidget(self.confirm_input)

        # Show / Hide Toggle Checkbox
        show_row = QHBoxLayout()
        self.show_cb = QPushButton("👁️ Show Passwords")
        self.show_cb.setObjectName("showToggleBtn")
        self.show_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.show_cb.clicked.connect(self.toggle_all_visibility)
        show_row.addWidget(self.show_cb)
        show_row.addStretch()
        layout.addLayout(show_row)

        # Status / Error Label
        self.status_lbl = QLabel("")
        self.status_lbl.setObjectName("statusLabel")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setWordWrap(True)
        layout.addWidget(self.status_lbl)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondaryBtn")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Save New Password")
        self.save_btn.setObjectName("saveBtn")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self.handle_save)
        btn_row.addWidget(self.save_btn)

        layout.addLayout(btn_row)

    def toggle_all_visibility(self):
        if self.current_input.echoMode() == QLineEdit.EchoMode.Password:
            mode = QLineEdit.EchoMode.Normal
            self.show_cb.setText("🔒 Hide Passwords")
        else:
            mode = QLineEdit.EchoMode.Password
            self.show_cb.setText("👁️ Show Passwords")

        self.current_input.setEchoMode(mode)
        self.new_input.setEchoMode(mode)
        self.confirm_input.setEchoMode(mode)

    def handle_save(self):
        curr = self.current_input.text()
        new_p = self.new_input.text()
        conf = self.confirm_input.text()

        if not curr:
            self.status_lbl.setText("❌ Please enter your current password.")
            self.current_input.setFocus()
            return

        if not new_p:
            self.status_lbl.setText("❌ New password cannot be empty.")
            self.new_input.setFocus()
            return

        if len(new_p.strip()) < 3:
            self.status_lbl.setText("❌ New password must be at least 3 characters.")
            self.new_input.setFocus()
            return

        if new_p != conf:
            self.status_lbl.setText("❌ New password and confirmation do not match.")
            self.confirm_input.setFocus()
            return

        success, msg = set_new_password(curr, new_p)
        if success:
            QMessageBox.information(
                self,
                "Password Updated",
                "Your password has been changed successfully!\n\n"
                "Please remember your new password for future launches."
            )
            self.accept()
        else:
            self.status_lbl.setText(f"❌ {msg}")
            if "Current password" in msg:
                self.current_input.selectAll()
                self.current_input.setFocus()

    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            }
            #dialogTitle {
                font-size: 16px;
                font-weight: 700;
                color: #0F172A;
            }
            #dialogSubtitle {
                font-size: 12px;
                color: #64748B;
                margin-bottom: 4px;
            }
            QLabel {
                font-size: 12px;
                font-weight: 600;
                color: #334155;
            }
            #formInput {
                background-color: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                color: #1E293B;
            }
            #formInput:focus {
                border: 1px solid #2563EB;
                background-color: #FFFFFF;
            }
            #showToggleBtn {
                background-color: transparent;
                border: none;
                color: #2563EB;
                font-size: 11px;
                font-weight: 600;
                padding: 4px;
            }
            #showToggleBtn:hover {
                text-decoration: underline;
            }
            #statusLabel {
                font-size: 11px;
                font-weight: 600;
                color: #DC2626;
                min-height: 18px;
            }
            #saveBtn {
                background-color: #2563EB;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 700;
                padding: 8px 16px;
                border-radius: 6px;
                border: none;
            }
            #saveBtn:hover {
                background-color: #1D4ED8;
            }
            #secondaryBtn {
                background-color: #F1F5F9;
                color: #475569;
                font-size: 13px;
                font-weight: 600;
                padding: 8px 14px;
                border-radius: 6px;
                border: 1px solid #CBD5E1;
            }
            #secondaryBtn:hover {
                background-color: #E2E8F0;
                color: #1E293B;
            }
        """)
