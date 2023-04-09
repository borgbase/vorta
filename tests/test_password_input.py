from vorta.views.partials.password_input import PasswordInput, PasswordLineEdit


def test_create_password_line_edit(qtbot):
    password_line_edit = PasswordLineEdit()
    qtbot.addWidget(password_line_edit)
    assert password_line_edit is not None


def test_password_line_get_password(qtbot):
    password_line_edit = PasswordLineEdit()
    qtbot.addWidget(password_line_edit)

    assert password_line_edit.get_password() == ""

    password_line_edit.setText("test")
    assert password_line_edit.get_password() == "test"


def test_password_line_visible(qtbot):
    password_line_edit = PasswordLineEdit()
    qtbot.addWidget(password_line_edit)
    assert not password_line_edit.visible

    password_line_edit.toggle_visibility()
    assert password_line_edit.visible


def test_password_line_error_state(qtbot):
    password_line_edit = PasswordLineEdit()
    qtbot.addWidget(password_line_edit)
    assert not password_line_edit.error_state
    assert password_line_edit.styleSheet() == ""

    password_line_edit.error_state = True
    assert password_line_edit.error_state
    assert password_line_edit.styleSheet() == "border: 2px solid red;"


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
def test_create_password_input(qtbot):
    password_input = PasswordInput()
    qtbot.addWidget(password_input.create_form_widget())
    assert password_input is not None

    # test default error state
    assert not password_input.passwordLineEdit.error_state
    assert not password_input.confirmLineEdit.error_state
