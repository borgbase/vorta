import os

import pytest
from PyQt5 import QtCore
from PyQt5.QtWidgets import QFileDialog, QDialogButtonBox, QMessageBox

from vorta.models import BackupProfileModel, SourceFileModel
from vorta.views.import_window import ImportWindow


def test_import_success(qapp, qtbot, rootdir, monkeypatch):
    # Do not change this file, as it also tests restoring from older schema versions
    GOOD_FILE = os.path.join(rootdir, 'profile_exports', 'valid.json')

    def getOpenFileName(*args, **kwargs):
        return [GOOD_FILE]

    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", getOpenFileName
    )

    main = qapp.main_window
    main.profile_import_action()
    import_dialog: ImportWindow = main.window
    import_dialog.overwriteExistingSettings.setChecked(True)

    qtbot.mouseClick(import_dialog.buttonBox.button(QDialogButtonBox.Ok), QtCore.Qt.LeftButton)
    qtbot.waitSignal(import_dialog.profile_imported, **pytest._wait_defaults)

    restored_profile = BackupProfileModel.get_or_none(name="Test Profile Restoration")
    assert restored_profile is not None
    restored_repo = restored_profile.repo
    assert restored_repo is not None
    assert len(SourceFileModel.select().where(SourceFileModel.profile == restored_profile)) == 3


def test_import_fail_not_json(qapp, qtbot, rootdir, monkeypatch):
    BAD_FILE = os.path.join(rootdir, 'profile_exports', 'invalid_no_json.json')

    def getOpenFileName(*args, **kwargs):
        return [BAD_FILE]

    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", getOpenFileName
    )

    alert_message = None

    def critical(widget, title, message):
        nonlocal alert_message
        alert_message = message

    monkeypatch.setattr(
        QMessageBox, "critical", critical
    )

    main = qapp.main_window
    main.profile_import_action()

    # assert somehow that an alert is shown
    assert alert_message == 'This file does not contain valid JSON.'


def test_export_success(qapp, qtbot, tmpdir, monkeypatch):
    FILE_PATH = os.path.join(tmpdir, "testresult.json")

    def getSaveFileName(*args, **kwargs):
        return [FILE_PATH]

    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", getSaveFileName
    )

    main = qapp.main_window
    main.profile_export_action()
    export_dialog = main.window

    qtbot.mouseClick(export_dialog.buttonBox.button(QDialogButtonBox.Save), QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: os.path.isfile(FILE_PATH))

    assert os.path.isfile(FILE_PATH)


def test_export_fail_unwritable(qapp, qtbot, tmpdir, monkeypatch):
    FILE_PATH = os.path.join(os.path.abspath(os.sep), "testresult.vortabackup")

    def getSaveFileName(*args, **kwargs):
        return [FILE_PATH]

    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", getSaveFileName
    )

    alert_message = None

    def critical(widget, title, message):
        nonlocal alert_message
        alert_message = message

    monkeypatch.setattr(
        QMessageBox, "critical", critical
    )

    main = qapp.main_window
    main.profile_export_action()
    export_dialog = main.window

    qtbot.mouseClick(export_dialog.buttonBox.button(QDialogButtonBox.Save), QtCore.Qt.LeftButton)

    assert 'could not be created' in alert_message
    assert not os.path.isfile(FILE_PATH)
