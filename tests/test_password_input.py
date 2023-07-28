import pytest
from PyQt6.QtWidgets import QFormLayout, QWidget
from vorta.views.partials.password_input import PasswordInput, PasswordLineEdit


def test_create_password_line_edit(qtbot):
    password_line_edit = PasswordLineEdit()
    qtbot.addWidget(password_line_edit)
    assert password_line_edit is not None


def test_password_line_get_password(qtbot):
    password_line_edit = PasswordLineEdit()
    qtbot.addWidget(password_line_edit)

    assert password_line_edit.get_password() == ""

    qtbot.keyClicks(password_line_edit, "test")
    assert password_line_edit.get_password() == "test"


def test_password_line_visible(qtbot):
    password_line_edit = PasswordLineEdit()
    qtbot.addWidget(password_line_edit)
    assert not password_line_edit.visible

    password_line_edit.toggle_visibility()
    assert password_line_edit.visible

    with pytest.raises(TypeError):
        password_line_edit.visible = "OK"


def test_password_line_error_state(qtbot):
    password_line_edit = PasswordLineEdit()
    qtbot.addWidget(password_line_edit)
    assert not password_line_edit.error_state
    assert password_line_edit.styleSheet() == ""

    password_line_edit.error_state = True
    assert password_line_edit.error_state
    assert password_line_edit.styleSheet() == "QLineEdit { border: 2px solid red; }"


def test_password_line_visibility_button(qtbot):
    password_line_edit = PasswordLineEdit(show_visibility_button=False)
    qtbot.addWidget(password_line_edit)
    assert not password_line_edit._show_visibility_button

    password_line_edit = PasswordLineEdit()
    qtbot.addWidget(password_line_edit)
    assert password_line_edit._show_visibility_button

    # test visibility button
    password_line_edit.showHideAction.trigger()
    assert password_line_edit.visible
    password_line_edit.showHideAction.trigger()
    assert not password_line_edit.visible


# PasswordInput
def test_create_password_input(qapp, qtbot):
    password_input = PasswordInput()
    qtbot.addWidget(password_input.create_form_widget(parent=qapp.main_window))
    assert password_input is not None

    assert not password_input.passwordLineEdit.error_state
    assert not password_input.confirmLineEdit.error_state


def test_password_input_get_password(qapp, qtbot):
    password_input = PasswordInput()
    qtbot.addWidget(password_input.create_form_widget(parent=qapp.main_window))

    assert password_input.get_password() == ""

    password_input.passwordLineEdit.setText("test")
    assert password_input.get_password() == "test"


def test_password_input_validation(qapp, qtbot):
    password_input = PasswordInput(minimum_length=10)
    qtbot.addWidget(password_input.create_form_widget(parent=qapp.main_window))

    qtbot.keyClicks(password_input.passwordLineEdit, "123456789")
    qtbot.keyClicks(password_input.confirmLineEdit, "123456789")

    assert password_input.passwordLineEdit.error_state
    assert password_input.validation_label.text() == "Passwords must be atleast 10 characters long."

    password_input.clear()
    qtbot.keyClicks(password_input.passwordLineEdit, "123456789")
    qtbot.keyClicks(password_input.confirmLineEdit, "test")

    assert password_input.passwordLineEdit.error_state
    assert password_input.confirmLineEdit.error_state
    assert password_input.validation_label.text() == "Passwords must be identical and atleast 10 characters long."

    password_input.clear()
    qtbot.keyClicks(password_input.passwordLineEdit, "1234567890")
    qtbot.keyClicks(password_input.confirmLineEdit, "test")

    assert not password_input.passwordLineEdit.error_state
    assert password_input.confirmLineEdit.error_state
    assert password_input.validation_label.text() == "Passwords must be identical."

    password_input.clear()
    qtbot.keyClicks(password_input.passwordLineEdit, "1234567890")
    qtbot.keyClicks(password_input.confirmLineEdit, "1234567890")

    assert not password_input.passwordLineEdit.error_state
    assert not password_input.confirmLineEdit.error_state
    assert password_input.validation_label.text() == ""


def test_password_input_validation_disabled(qapp, qtbot):
    password_input = PasswordInput(show_error=False)
    qtbot.addWidget(password_input.create_form_widget(parent=qapp.main_window))

    qtbot.keyClicks(password_input.passwordLineEdit, "test")
    qtbot.keyClicks(password_input.confirmLineEdit, "test")

    assert not password_input.passwordLineEdit.error_state
    assert not password_input.confirmLineEdit.error_state
    assert password_input.validation_label.text() == ""

    password_input.set_validation_enabled(True)
    qtbot.keyClicks(password_input.passwordLineEdit, "s")
    qtbot.keyClicks(password_input.confirmLineEdit, "a")

    assert password_input.passwordLineEdit.error_state
    assert password_input.confirmLineEdit.error_state
    assert password_input.validation_label.text() == "Passwords must be identical and atleast 9 characters long."

    password_input.set_validation_enabled(False)
    assert not password_input.passwordLineEdit.error_state
    assert not password_input.confirmLineEdit.error_state
    assert password_input.validation_label.text() == ""


def test_password_input_set_label(qapp, qtbot):
    password_input = PasswordInput(label=["test", "test2"])
    qtbot.addWidget(password_input.create_form_widget(parent=qapp.main_window))

    assert password_input._label_password.text() == "test"
    assert password_input._label_confirm.text() == "test2"

    password_input.set_labels("test3", "test4")
    assert password_input._label_password.text() == "test3"
    assert password_input._label_confirm.text() == "test4"


def test_password_input_add_form_to_layout(qapp, qtbot):
    password_input = PasswordInput()

    widget = QWidget()
    form_layout = QFormLayout(widget)

    qtbot.addWidget(widget)
    password_input.add_form_to_layout(form_layout)

    assert form_layout.itemAt(0, QFormLayout.ItemRole.LabelRole).widget() == password_input._label_password
    assert form_layout.itemAt(0, QFormLayout.ItemRole.FieldRole).widget() == password_input.passwordLineEdit
    assert form_layout.itemAt(1, QFormLayout.ItemRole.LabelRole).widget() == password_input._label_confirm
    assert form_layout.itemAt(1, QFormLayout.ItemRole.FieldRole).widget() == password_input.confirmLineEdit
