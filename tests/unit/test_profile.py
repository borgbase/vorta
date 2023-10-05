from PyQt6 import QtCore
from PyQt6.QtWidgets import QDialogButtonBox, QMessageBox, QToolTip
from vorta.store.models import BackupProfileModel


def test_profile_add_delete(qapp, qtbot, mocker):
    """Tests adding and deleting profiles."""
    main = qapp.main_window

    # add profile and ensure it is created as intended
    qtbot.mouseClick(main.profileAddButton, QtCore.Qt.MouseButton.LeftButton)
    add_profile_window = main.window
    qtbot.keyClicks(add_profile_window.profileNameField, 'Test Profile')
    save_button = add_profile_window.buttonBox.button(QDialogButtonBox.StandardButton.Save)
    qtbot.mouseClick(save_button, QtCore.Qt.MouseButton.LeftButton)
    assert BackupProfileModel.get_or_none(name='Test Profile') is not None
    assert main.profileSelector.currentText() == 'Test Profile'

    # delete the new profile and ensure it is no longer available.
    mocker.patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes)
    qtbot.mouseClick(main.profileDeleteButton, QtCore.Qt.MouseButton.LeftButton)
    assert BackupProfileModel.get_or_none(name='Test Profile') is None
    assert main.profileSelector.currentText() == 'Default'

    # attempt to delete the last remaining profile
    # see that it cannot be deleted, a warning is displayed, and the profile remains
    warning = mocker.patch.object(QToolTip, 'showText')
    qtbot.mouseClick(main.profileDeleteButton, QtCore.Qt.MouseButton.LeftButton)
    assert "Cannot delete the last profile." in warning.call_args[0][1]
    assert BackupProfileModel.get_or_none(name='Default') is not None
    assert main.profileSelector.currentText() == 'Default'


def test_profile_edit(qapp, qtbot):
    """Tests editing/renaming a profile"""
    main = qapp.main_window

    # click to rename profile, clear the name field, type new profile name
    qtbot.mouseClick(main.profileRenameButton, QtCore.Qt.MouseButton.LeftButton)
    edit_profile_window = main.window
    edit_profile_window.profileNameField.setText("")
    qtbot.keyClicks(edit_profile_window.profileNameField, 'Test Profile')
    save_button = edit_profile_window.buttonBox.button(QDialogButtonBox.StandardButton.Save)
    qtbot.mouseClick(save_button, QtCore.Qt.MouseButton.LeftButton)

    # assert a profile by the old name no longer exists, and the newly named profile does exist and is selected.
    assert BackupProfileModel.get_or_none(name='Default') is None
    assert BackupProfileModel.get_or_none(name='Test Profile') is not None
    assert main.profileSelector.currentText() == 'Test Profile'
