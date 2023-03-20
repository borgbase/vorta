from PyQt5 import QtCore
from PyQt5.QtWidgets import QAction, QFormLayout, QLabel, QLineEdit, QWidget
from vorta.i18n import trans_late, translate
from vorta.views.utils import get_colored_icon


class PasswordLineEdit(QLineEdit):
    password_too_short = QtCore.pyqtSignal()

    def __init__(self, parent=None, show_visibility_button=True):
        super().__init__(parent)

        self._show_visibility_button = show_visibility_button

        self.setEchoMode(QLineEdit.Password)

        if self._show_visibility_button:
            self.showHideAction = QAction(self.tr("Show password"), self)
            self.showHideAction.setCheckable(True)
            self.showHideAction.toggled.connect(self._toggle_password_visibility)
            self.showHideAction.setIcon(get_colored_icon("eye"))
            self.addAction(self.showHideAction, QLineEdit.TrailingPosition)

    def get_password(self):
        """Return password text"""
        return self.text()

    def _toggle_password_visibility(self):
        if self.echoMode() == QLineEdit.Password:
            self.setEchoMode(QLineEdit.Normal)
            self.showHideAction.setIcon(get_colored_icon("eye"))
        else:
            self.setEchoMode(QLineEdit.Password)
            self.showHideAction.setIcon(get_colored_icon("eye-slash"))

    def set_error_state(self, error):
        """Display red border if password is not valid"""
        if error:
            self.setStyleSheet('border: 2px solid red;')
        else:
            self.setStyleSheet('')


class PasswordInput(QWidget):
    # password label changed signal
    passwordLabelChanged = QtCore.pyqtSignal(str)

    def __init__(self, parent=None, form_layout=None, minimum_length=9, show_error=True, label: list = None):
        super().__init__(parent)
        self._minimum_length = minimum_length
        self._show_error = show_error

        if label:
            self._label_1 = QLabel(label[0])
            self._label_2 = QLabel(label[1])
        else:
            self._label_1 = QLabel(self.tr("Enter passphrase:"))
            self._label_2 = QLabel(self.tr("Confirm passphrase:"))

        # Create password line edits
        self.passwordLineEdit = PasswordLineEdit(parent=self)
        self.confirmLineEdit = PasswordLineEdit(parent=self)
        self.password_label = QLabel("")

        self.passwordLineEdit.editingFinished.connect(self.validate)
        self.confirmLineEdit.textChanged.connect(self.validate)

        # form_layout = parent.layout() if isinstance(parent, QFormLayout) else None
        if form_layout is not None:
            form_layout.addRow(self._label_1, self.passwordLineEdit)
            form_layout.addRow(self._label_2, self.confirmLineEdit)
            form_layout.addRow(self.password_label)
        else:
            password_form = QFormLayout(self)
            password_form.setContentsMargins(0, 0, 0, 0)
            password_form.addRow(self._label_1, self.passwordLineEdit)
            password_form.addRow(self._label_2, self.confirmLineEdit)
            password_form.addRow(self.password_label)

            password_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

            self.setLayout(password_form)

    def set_labels(self, label_1, label_2):
        self._label_1 = label_1
        self._label_2 = label_2

    def set_error_label(self, text):
        self.password_label.setText(translate('utils', text))

    def set_validation(self, enable: bool):
        self._show_error = enable
        if not enable:
            self.set_error_label("")

    def get_password(self):
        return self.passwordLineEdit.text()

    def validate(self):
        if not self._show_error:
            return True

        first_pass = self.passwordLineEdit.text()
        second_pass = self.confirmLineEdit.text()

        pass_equal = first_pass == second_pass
        pass_long = len(first_pass) >= self._minimum_length

        self.passwordLineEdit.set_error_state(False)
        self.confirmLineEdit.set_error_state(False)
        msg = ""

        if not pass_long and not pass_equal:
            self.passwordLineEdit.set_error_state(True)
            self.confirmLineEdit.set_error_state(True)
            msg = trans_late('utils', "Passwords must be identical and greater than 8 characters long.")
        elif not pass_equal:
            self.confirmLineEdit.set_error_state(True)
            msg = trans_late('utils', "Passwords must be identical.")
        elif not pass_long:
            self.confirmLineEdit.set_error_state(True)
            msg = trans_late('utils', "Passwords must be greater than 8 characters long.")

        # fire signal
        self.passwordLabelChanged.emit(msg)
        self.set_error_label(msg)
        return not bool(msg)
