import pytest
from PyQt5 import QtCore
from PyQt5.QtWidgets import QDialogButtonBox
from .conftest import delete_current_profile
from vorta.models import BackupProfileModel


def test_profile_add(qapp, qtbot):
    main = qapp.main_window
    qtbot.mouseClick(main.profileAddButton, QtCore.Qt.LeftButton)

    add_profile_window = main.window
    qtbot.addWidget(add_profile_window)
    qtbot.waitUntil(lambda: add_profile_window == qapp.activeWindow(), **pytest._wait_defaults)

    qtbot.keyClicks(add_profile_window.profileNameField, 'Test Profile')
    qtbot.mouseClick(add_profile_window.buttonBox.button(QDialogButtonBox.Save), QtCore.Qt.LeftButton)

    assert BackupProfileModel.get_or_none(name='Test Profile') is not None
    assert main.profileSelector.currentText() == 'Test Profile'

    delete_current_profile(qapp)


def test_profile_edit(qapp, qtbot):
    main = qapp.main_window
    qtbot.mouseClick(main.profileRenameButton, QtCore.Qt.LeftButton)

    edit_profile_window = main.window
    qtbot.addWidget(edit_profile_window)
    qtbot.waitUntil(lambda: edit_profile_window == qapp.activeWindow(), **pytest._wait_defaults)

    edit_profile_window.profileNameField.setText("")
    qtbot.keyClicks(edit_profile_window.profileNameField, 'Test Profile')
    qtbot.mouseClick(edit_profile_window.buttonBox.button(QDialogButtonBox.Save), QtCore.Qt.LeftButton)

    assert BackupProfileModel.get_or_none(name='Default') is None
    assert BackupProfileModel.get_or_none(name='Test Profile') is not None
    assert main.profileSelector.currentText() == 'Test Profile'
