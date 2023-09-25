from typing import Optional

from PyQt6.QtCore import QObject
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QFormLayout, QLabel, QLineEdit, QWidget

from vorta.i18n import translate
from vorta.views.utils import get_colored_icon


class PasswordLineEdit(QLineEdit):
    def __init__(self, *, parent: Optional[QWidget] = None, show_visibility_button: bool = True) -> None:
        super().__init__(parent)

        self._show_visibility_button = show_visibility_button
        self._error_state = False
        self._visible = False

        self.setEchoMode(QLineEdit.EchoMode.Password)

        if self._show_visibility_button:
            self.showHideAction = QAction(self.tr("Show password"), self)
            self.showHideAction.setCheckable(True)
            self.showHideAction.toggled.connect(self.toggle_visibility)
            self.showHideAction.setIcon(get_colored_icon("eye"))
            self.addAction(self.showHideAction, QLineEdit.ActionPosition.TrailingPosition)

    def get_password(self) -> str:
        """Return password text"""
        return self.text()

    @property
    def visible(self) -> bool:
        """Return password visibility"""
        return self._visible

    @visible.setter
    def visible(self, value: bool) -> None:
        """Set password visibility"""
        if not isinstance(value, bool):
            raise TypeError("visible must be a boolean value")
        self._visible = value
        self.setEchoMode(QLineEdit.EchoMode.Normal if self._visible else QLineEdit.EchoMode.Password)

        if self._show_visibility_button:
            if self._visible:
                self.showHideAction.setIcon(get_colored_icon("eye-slash"))
                self.showHideAction.setText(self.tr("Hide password"))

            else:
                self.showHideAction.setIcon(get_colored_icon("eye"))
                self.showHideAction.setText(self.tr("Show password"))

    def toggle_visibility(self) -> None:
        """Toggle password visibility"""
        self.visible = not self._visible

    @property
    def error_state(self) -> bool:
        """Return error state"""
        return self._error_state

    @error_state.setter
    def error_state(self, error: bool) -> None:
        """Set error state and update style"""
        self._error_state = error
        if error:
            self.setStyleSheet("QLineEdit { border: 2px solid red; }")
        else:
            self.setStyleSheet('')


class PasswordInput(QObject):
    def __init__(self, *, parent=None, minimum_length: int = 9, show_error: bool = True, label: list = None) -> None:
        super().__init__(parent)
        self._minimum_length = minimum_length
        self._show_error = show_error

        if label:
            self._label_password = QLabel(label[0])
            self._label_confirm = QLabel(label[1])
        else:
            self._label_password = QLabel(self.tr("Enter passphrase:"))
            self._label_confirm = QLabel(self.tr("Confirm passphrase:"))

        # Create password line edits
        self.passwordLineEdit = PasswordLineEdit()
        self.confirmLineEdit = PasswordLineEdit()
        self.validation_label = QLabel("")

        self.passwordLineEdit.editingFinished.connect(self.on_editing_finished)
        self.confirmLineEdit.textChanged.connect(self.validate)

    def on_editing_finished(self) -> None:
        self.passwordLineEdit.editingFinished.disconnect(self.on_editing_finished)
        self.passwordLineEdit.textChanged.connect(self.validate)
        self.validate()

    def set_labels(self, label_1: str, label_2: str) -> None:
        self._label_password.setText(label_1)
        self._label_confirm.setText(label_2)

    def set_error_label(self, text: str) -> None:
        self.validation_label.setText(text)

    def set_validation_enabled(self, enable: bool) -> None:
        self._show_error = enable
        self.passwordLineEdit.error_state = False
        self.confirmLineEdit.error_state = False
        if not enable:
            self.set_error_label("")

    def clear(self) -> None:
        self.passwordLineEdit.clear()
        self.confirmLineEdit.clear()
        self.passwordLineEdit.error_state = False
        self.confirmLineEdit.error_state = False
        self.set_error_label("")

    def get_password(self) -> str:
        return self.passwordLineEdit.text()

    def validate(self) -> bool:
        if not self._show_error:
            return True

        first_pass = self.passwordLineEdit.text()
        second_pass = self.confirmLineEdit.text()

        pass_equal = first_pass == second_pass
        pass_long = len(first_pass) >= self._minimum_length

        self.passwordLineEdit.error_state = False
        self.confirmLineEdit.error_state = False
        self.set_error_label("")

        if not pass_long and not pass_equal:
            self.passwordLineEdit.error_state = True
            self.confirmLineEdit.error_state = True
            self.set_error_label(
                translate('PasswordInput', "Passwords must be identical and at least {0} characters long.").format(
                    self._minimum_length
                )
            )
        elif not pass_equal:
            self.confirmLineEdit.error_state = True
            self.set_error_label(translate('PasswordInput', "Passwords must be identical."))
        elif not pass_long:
            self.passwordLineEdit.error_state = True
            self.set_error_label(
                translate('PasswordInput', "Passwords must be at least {0} characters long.").format(
                    self._minimum_length
                )
            )

        return not bool(self.validation_label.text())

    def add_form_to_layout(self, form_layout: QFormLayout) -> None:
        """Adds form to layout"""
        form_layout.addRow(self._label_password, self.passwordLineEdit)
        form_layout.addRow(self._label_confirm, self.confirmLineEdit)
        form_layout.addRow(self.validation_label)

    def create_form_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        """ "Creates and Returns a new QWidget with form layout"""
        widget = QWidget(parent=parent)
        form_layout = QFormLayout(widget)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.add_form_to_layout(form_layout)
        widget.setLayout(form_layout)
        return widget
