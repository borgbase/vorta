import os
from PyQt5 import QtCore
from PyQt5.QtWidgets import QFileDialog, QDialogButtonBox
from .conftest import delete_current_profile
from vorta.models import BackupProfileModel, SourceFileModel


def test_restore_success(qapp, qtbot, rootdir, monkeypatch):
    # Do not change this file, as it also tests restoring from older schema versions
    GOOD_FILE = os.path.join(rootdir, "testcase.vortabackup")

    def getOpenFileName(*args, **kwargs):
        return [GOOD_FILE]

    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", getOpenFileName
    )

    main = qapp.main_window
    main.restoreAction.trigger()
    restore_dialog = main.window

    qtbot.mouseClick(restore_dialog.fileButton, QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: restore_dialog.locationLabel.text() == GOOD_FILE, timeout=5000)

    qtbot.mouseClick(restore_dialog.buttonBox.button(QDialogButtonBox.Open), QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: "sucessfully" in restore_dialog.errors.text(), timeout=5000)

    restored_profile = BackupProfileModel.get_or_none(name="Test Profile Restoration")
    assert restored_profile is not None
    restored_repo = restored_profile.repo
    assert restored_repo is not None
    assert len(SourceFileModel.select().where(SourceFileModel.profile == restored_profile)) == 3
    assert main.profileSelector.currentText() == "Test Profile Restoration"

    delete_current_profile(qapp)
    qtbot.mouseClick(restore_dialog.buttonBox.button(QDialogButtonBox.Cancel), QtCore.Qt.LeftButton)


def test_restore_fail(qapp, qtbot, rootdir, monkeypatch):
    BAD_FILE = os.path.join(rootdir, "invalid.vortabackup")

    def getOpenFileName(*args, **kwargs):
        return [BAD_FILE]

    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", getOpenFileName
    )
    main = qapp.main_window
    main.restoreAction.trigger()
    restore_dialog = main.window

    qtbot.mouseClick(restore_dialog.fileButton, QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: restore_dialog.locationLabel.text() == BAD_FILE, timeout=5000)

    qtbot.mouseClick(restore_dialog.buttonBox.button(QDialogButtonBox.Open), QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: restore_dialog.errors.text() == "Invalid backup file", timeout=5000)
    qtbot.mouseClick(restore_dialog.buttonBox.button(QDialogButtonBox.Cancel), QtCore.Qt.LeftButton)


def test_backup_success(qapp, qtbot, rootdir, monkeypatch):
    FILE_PATH = os.path.join(os.path.expanduser("~"), "testresult.vortabackup")

    def getSaveFileName(*args, **kwargs):
        return [FILE_PATH]

    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", getSaveFileName
    )

    main = qapp.main_window
    main.backupAction.trigger()
    restore_dialog = main.window

    qtbot.mouseClick(restore_dialog.fileButton, QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: restore_dialog.locationLabel.text() == FILE_PATH, timeout=5000)

    qtbot.mouseClick(restore_dialog.buttonBox.button(QDialogButtonBox.Save), QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: "written to" in restore_dialog.errors.text(), timeout=5000)

    assert os.path.isfile(FILE_PATH)
    qtbot.mouseClick(restore_dialog.buttonBox.button(QDialogButtonBox.Cancel), QtCore.Qt.LeftButton)


def test_backup_fail(qapp, qtbot, rootdir, monkeypatch):
    FILE_PATH = os.path.join(os.path.abspath(os.sep), "testresult.vortabackup")

    def getSaveFileName(*args, **kwargs):
        return [FILE_PATH]

    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", getSaveFileName
    )

    main = qapp.main_window
    main.backupAction.trigger()
    restore_dialog = main.window

    qtbot.mouseClick(restore_dialog.fileButton, QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: restore_dialog.locationLabel.text() == FILE_PATH, timeout=5000)

    qtbot.mouseClick(restore_dialog.buttonBox.button(QDialogButtonBox.Save), QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: "unwritable" in restore_dialog.errors.text(), timeout=5000)

    assert not os.path.isfile(FILE_PATH)
    qtbot.mouseClick(restore_dialog.buttonBox.button(QDialogButtonBox.Cancel), QtCore.Qt.LeftButton)
