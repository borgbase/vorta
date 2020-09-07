from PyQt5 import QtCore
import PyQt5.QtWidgets
import os

from vorta.views.backup_window import RestoreWindow


def test_restore_success(qapp, qtbot, rootdir, monkeypatch):
    GOOD_FILE = os.path.join(rootdir, "testcase.vortabackup")

    def getOpenFileName(*args, **kwargs):
        return [GOOD_FILE]

    monkeypatch.setattr(
        PyQt5.QtWidgets.QFileDialog, "getOpenFileName", getOpenFileName
    )

    main = qapp.main_window
    restore_dialog = RestoreWindow(parent=main)

    qtbot.mouseClick(restore_dialog.fileButton, QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: restore_dialog.locationLabel.text() == GOOD_FILE, timeout=5000)

    qtbot.mouseClick(restore_dialog.saveButton, QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: restore_dialog.errors.text() == "", timeout=5000)


def test_restore_fail(qapp, qtbot, rootdir, monkeypatch):
    BAD_FILE = os.path.join(rootdir, "invalid.vortabackup")

    def getOpenFileName(*args, **kwargs):
        return [BAD_FILE]

    monkeypatch.setattr(
        PyQt5.QtWidgets.QFileDialog, "getOpenFileName", getOpenFileName
    )
    main = qapp.main_window
    restore_dialog = RestoreWindow(parent=main)

    qtbot.mouseClick(restore_dialog.fileButton, QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: restore_dialog.locationLabel.text() == BAD_FILE, timeout=5000)

    qtbot.mouseClick(restore_dialog.saveButton, QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: restore_dialog.errors.text() == "Invalid backup file", timeout=5000)
    qtbot.mouseClick(restore_dialog.cancelButton, QtCore.Qt.LeftButton)
