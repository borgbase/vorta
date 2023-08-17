import os
from pathlib import Path

import pytest
from PyQt6 import QtCore
from PyQt6.QtWidgets import QDialogButtonBox, QFileDialog, QMessageBox
from vorta.profile_export import VersionException
from vorta.store.models import BackupProfileModel, SourceFileModel
from vorta.views.import_window import ImportWindow

VALID_IMPORT_FILE = Path(__file__).parent / 'profile_exports' / 'valid.json'


def test_import_success(qapp, qtbot, rootdir, monkeypatch):
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: [VALID_IMPORT_FILE])
    monkeypatch.setattr(QMessageBox, 'information', lambda *args: None)

    main = qapp.main_window
    main.profile_import_action()
    import_dialog: ImportWindow = main.window
    import_dialog.overwriteExistingSettings.setChecked(True)

    qtbot.mouseClick(
        import_dialog.buttonBox.button(QDialogButtonBox.StandardButton.Ok), QtCore.Qt.MouseButton.LeftButton
    )
    qtbot.waitSignal(import_dialog.profile_imported, **pytest._wait_defaults)

    restored_profile = BackupProfileModel.get_or_none(name="Test Profile Restoration")
    assert restored_profile is not None

    restored_repo = restored_profile.repo
    assert restored_repo is not None
    assert len(SourceFileModel.select().where(SourceFileModel.profile == restored_profile)) == 3


@pytest.mark.parametrize(
    "exception, error_message",
    [
        (AttributeError, "Schema upgrade failure"),
        (VersionException, "Newer profile_export export files cannot be used on older versions"),
        (PermissionError, "Cannot read profile_export export file due to permission error"),
        (FileNotFoundError, "Profile export file not found"),
    ],
)
def test_import_exceptions(qapp, qtbot, rootdir, monkeypatch, mocker, exception, error_message):
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: [VALID_IMPORT_FILE])
    monkeypatch.setattr(QMessageBox, 'information', lambda *args: None)

    main = qapp.main_window
    main.profile_import_action()
    import_dialog: ImportWindow = main.window
    import_dialog.overwriteExistingSettings.setChecked(True)

    def raise_exception(*args, **kwargs):
        raise exception

    # force an exception and mock the error QMessageBox
    monkeypatch.setattr(import_dialog.profile_export, 'to_db', raise_exception)
    mock_messagebox = mocker.patch.object(QMessageBox, "critical")

    qtbot.mouseClick(
        import_dialog.buttonBox.button(QDialogButtonBox.StandardButton.Ok), QtCore.Qt.MouseButton.LeftButton
    )

    # assert the correct error appears, and the profile does not get added
    mock_messagebox.assert_called_once()
    assert error_message in mock_messagebox.call_args[0][2]
    assert BackupProfileModel.get_or_none(name="Test Profile Restoration") is None


def test_import_bootstrap_success(qapp, mocker):
    mocked_unlink = mocker.MagicMock()
    mocker.patch.object(Path, 'unlink', mocked_unlink)
    qapp.bootstrap_profile(Path(VALID_IMPORT_FILE))

    assert mocked_unlink.called

    restored_profile = BackupProfileModel.get_or_none(name="Test Profile Restoration")
    assert restored_profile is not None

    restored_repo = restored_profile.repo
    assert restored_repo is not None

    assert len(SourceFileModel.select().where(SourceFileModel.profile == restored_profile)) == 3
    assert BackupProfileModel.select().count() == 2


def test_import_fail_not_json(qapp, rootdir, monkeypatch):
    BAD_FILE = os.path.join(rootdir, 'profile_exports', 'invalid_no_json.json')

    def getOpenFileName(*args, **kwargs):
        return [BAD_FILE]

    monkeypatch.setattr(QFileDialog, "getOpenFileName", getOpenFileName)

    alert_message = None

    def critical(widget, title, message):
        nonlocal alert_message
        alert_message = message

    monkeypatch.setattr(QMessageBox, "critical", critical)

    main = qapp.main_window
    main.profile_import_action()

    # assert somehow that an alert is shown
    assert alert_message == 'This file does not contain valid JSON: Expecting value: line 1 column 1 (char 0)'


def test_export_success(qapp, qtbot, tmpdir, monkeypatch):
    FILE_PATH = os.path.join(tmpdir, "testresult.json")

    def getSaveFileName(*args, **kwargs):
        return [FILE_PATH]

    monkeypatch.setattr(QFileDialog, "getSaveFileName", getSaveFileName)

    main = qapp.main_window
    main.profile_export_action()
    export_dialog = main.window

    qtbot.mouseClick(
        export_dialog.buttonBox.button(QDialogButtonBox.StandardButton.Save), QtCore.Qt.MouseButton.LeftButton
    )
    qtbot.waitUntil(lambda: os.path.isfile(FILE_PATH))

    assert os.path.isfile(FILE_PATH)


def test_export_fail_unwritable(qapp, qtbot, monkeypatch):
    FILE_PATH = os.path.join(os.path.abspath(os.sep), "testresult.vortabackup")

    def getSaveFileName(*args, **kwargs):
        return [FILE_PATH]

    monkeypatch.setattr(QFileDialog, "getSaveFileName", getSaveFileName)

    alert_message = None

    def critical(widget, title, message):
        nonlocal alert_message
        alert_message = message

    monkeypatch.setattr(QMessageBox, "critical", critical)

    main = qapp.main_window
    main.profile_export_action()
    export_dialog = main.window

    qtbot.mouseClick(
        export_dialog.buttonBox.button(QDialogButtonBox.StandardButton.Save), QtCore.Qt.MouseButton.LeftButton
    )

    assert 'could not be created' in alert_message
    assert not os.path.isfile(FILE_PATH)
