from PyQt5 import QtCore
from PyQt5.QtWidgets import QDialogButtonBox

from vorta.views.profile_add_edit_dialog import AddProfileWindow, EditProfileWindow
from vorta.models import BackupProfileModel


def test_profile_add(qapp, qtbot):
    main = qapp.main_window
    add_profile_window = AddProfileWindow(main)
    qtbot.addWidget(add_profile_window)

    # Add a new profile
    qtbot.keyClicks(add_profile_window.profileNameField, 'Test Profile')
    qtbot.mouseClick(add_profile_window.buttonBox.button(QDialogButtonBox.Save), QtCore.Qt.LeftButton)
    assert BackupProfileModel.get_or_none(name='Test Profile') is not None


def test_profile_edit(qapp, qtbot):
    main = qapp.main_window
    edit_profile_window = EditProfileWindow(main, rename_existing_id=main.profileSelector.currentData())
    qtbot.addWidget(edit_profile_window)

    # Edit profile name
    edit_profile_window.profileNameField.setText("")
    qtbot.keyClicks(edit_profile_window.profileNameField, 'Test Profile')
    qtbot.mouseClick(edit_profile_window.buttonBox.button(QDialogButtonBox.Save), QtCore.Qt.LeftButton)
    assert BackupProfileModel.get_or_none(name='Default') is None
    assert BackupProfileModel.get_or_none(name='Test Profile') is not None
