from PyQt5 import QtCore
from PyQt5.QtWidgets import QDialogButtonBox

from vorta.models import BackupProfileModel


def test_profile_add(qapp, qtbot):
    def on_timeout():
        # Add a new profile
        add_profile_window = qapp.activeWindow()
        qtbot.addWidget(add_profile_window)
        qtbot.keyClicks(add_profile_window.profileNameField, 'Test Profile')
        qtbot.mouseClick(add_profile_window.buttonBox.button(QDialogButtonBox.Save), QtCore.Qt.LeftButton)

    main = qapp.main_window
    QtCore.QTimer.singleShot(1000, on_timeout)  # Run remaining async because exec_ blocks
    qtbot.mouseClick(main.profileAddButton, QtCore.Qt.LeftButton)
    assert BackupProfileModel.get_or_none(name='Test Profile') is not None
    qtbot.waitUntil(lambda: main.profileSelector.currentText() == 'Test Profile')


def test_profile_edit(qapp, qtbot):
    def on_timeout():
        # Edit profile name
        edit_profile_window = qapp.activeWindow()
        qtbot.addWidget(edit_profile_window)
        edit_profile_window.profileNameField.setText("")
        qtbot.keyClicks(edit_profile_window.profileNameField, 'Test Profile')
        qtbot.mouseClick(edit_profile_window.buttonBox.button(QDialogButtonBox.Save), QtCore.Qt.LeftButton)

    main = qapp.main_window
    QtCore.QTimer.singleShot(1000, on_timeout)  # Run remaining async because exec_ blocks
    main.renameAction.trigger()
    assert BackupProfileModel.get_or_none(name='Default') is None
    assert BackupProfileModel.get_or_none(name='Test Profile') is not None
    qtbot.waitUntil(lambda: main.profileSelector.currentText() == 'Test Profile')
