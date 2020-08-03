from PyQt5.QtWidgets import QDialogButtonBox
from PyQt5 import QtCore
import os

from vorta.views.backup_window import RestoreWindow
from vorta.models import BackupProfileModel


def test_restore_success(qapp, qtbot, rootdir):
    main = qapp.main_window
    restore_dialog = RestoreWindow(BackupProfileModel.get(id=main.profileSelector.currentData()))
    restore_dialog.saveButton.setEnabled(True)
    restore_dialog.locationLabel.setText(os.path.join(rootdir, "testcase.vortabackup"))
    qtbot.mouseClick(restore_dialog.saveButton, QtCore.Qt.LeftButton)
    assert(restore_dialog.errors.text() == "")


def test_restore_fail(qapp, qtbot, rootdir):
    main = qapp.main_window
    restore_dialog = RestoreWindow(BackupProfileModel.get(id=main.profileSelector.currentData()))
    restore_dialog.saveButton.setEnabled(True)
    restore_dialog.locationLabel.setText(os.path.join(rootdir, "invalid.vortabackup"))
    qtbot.mouseClick(restore_dialog.saveButton, QtCore.Qt.LeftButton)
    assert(restore_dialog.errors.text() == "Invalid backup file")
    qtbot.mouseClick(restore_dialog.cancelButton, QtCore.Qt.LeftButton)
