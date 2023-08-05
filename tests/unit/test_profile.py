from PyQt6 import QtCore
from PyQt6.QtWidgets import QDialogButtonBox
from vorta.store.models import BackupProfileModel


def test_profile_add(qapp, qtbot):
    main = qapp.main_window
    qtbot.mouseClick(main.profileAddButton, QtCore.Qt.MouseButton.LeftButton)

    add_profile_window = main.window
    # qtbot.addWidget(add_profile_window)

    qtbot.keyClicks(add_profile_window.profileNameField, 'Test Profile')
    qtbot.mouseClick(
        add_profile_window.buttonBox.button(QDialogButtonBox.StandardButton.Save), QtCore.Qt.MouseButton.LeftButton
    )

    assert BackupProfileModel.get_or_none(name='Test Profile') is not None
    assert main.profileSelector.currentText() == 'Test Profile'


def test_profile_edit(qapp, qtbot):
    main = qapp.main_window
    qtbot.mouseClick(main.profileRenameButton, QtCore.Qt.MouseButton.LeftButton)

    edit_profile_window = main.window
    # qtbot.addWidget(edit_profile_window)

    edit_profile_window.profileNameField.setText("")
    qtbot.keyClicks(edit_profile_window.profileNameField, 'Test Profile')
    qtbot.mouseClick(
        edit_profile_window.buttonBox.button(QDialogButtonBox.StandardButton.Save), QtCore.Qt.MouseButton.LeftButton
    )

    assert BackupProfileModel.get_or_none(name='Default') is None
    assert BackupProfileModel.get_or_none(name='Test Profile') is not None
    assert main.profileSelector.currentText() == 'Test Profile'
