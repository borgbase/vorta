from PyQt5 import QtCore
from PyQt5.QtWidgets import QAction, QHBoxLayout, QLineEdit, QWidget
from vorta.views.utils import get_colored_icon


class PasswordInput(QWidget):
    password_too_short = QtCore.pyqtSignal()
    textChanged = QtCore.pyqtSignal()

    def __init__(self, parent=None, minimum_length=6, show_visibility_button=True, show_error=True, match_with=None):
        super().__init__(parent)
        self._minimum_length = minimum_length
        self._show_visibility_button = show_visibility_button
        self.show_error = show_error
        self.match_with = match_with

        self._password_edit = QLineEdit(self)
        self._password_edit.setEchoMode(QLineEdit.Password)

        self._password_edit.textChanged.connect(self.textChanged)

        if self._show_visibility_button:
            self.showHideAction = QAction(self.tr("Show password"), self)
            self.showHideAction.setCheckable(True)
            self.showHideAction.toggled.connect(self._toggle_password_visibility)
            self.showHideAction.setIcon(get_colored_icon("eye"))
            self._password_edit.addAction(self.showHideAction, QLineEdit.TrailingPosition)

        if self.show_error:
            self._password_edit.editingFinished.connect(self._check_password_length)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._password_edit)
        self.setLayout(layout)

    # def set_match_with(self, match_with):
    #     self.match_with = match_with

    def _check_password_length(self):
        if len(self._password_edit.text()) < self._minimum_length:
            self.password_too_short.emit()
            self.set_error_state(True)
        elif self.match_with is not None and self._password_edit.text() != self.match_with.text():
            self.set_error_state(True)
        else:
            self.set_error_state(False)

    def text(self):
        """Return password value"""
        return self._password_edit.text()

    def setText(self, text):
        """Set password value"""
        self._password_edit.setText(text)

    def _toggle_password_visibility(self):
        if self._password_edit.echoMode() == QLineEdit.Password:
            self._password_edit.setEchoMode(QLineEdit.Normal)
            self.showHideAction.setIcon(get_colored_icon("eye"))
        else:
            self._password_edit.setEchoMode(QLineEdit.Password)
            self.showHideAction.setIcon(get_colored_icon("eye-slash"))

    def set_error_state(self, error):
        """Display red border if password is not valid"""
        if error:
            self._password_edit.setStyleSheet('border: 2px solid red;')
        else:
            self._password_edit.setStyleSheet('')
