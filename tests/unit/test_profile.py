import tempfile

from PyQt6 import QtCore
from PyQt6.QtWidgets import QDialogButtonBox, QFileDialog, QMessageBox, QToolTip
from vorta.store.models import BackupProfileModel, SourceFileModel
from vorta.views.export_window import ExportWindow


def test_profile_add_delete(qapp, qtbot, mocker):
    """Tests adding and deleting profiles."""
    main = qapp.main_window

    # add profile and ensure it is created as intended
    main.profile_add_action()
    add_profile_window = main.window
    qtbot.keyClicks(add_profile_window.profileNameField, 'Test Profile')
    save_button = add_profile_window.buttonBox.button(QDialogButtonBox.StandardButton.Save)
    qtbot.mouseClick(save_button, QtCore.Qt.MouseButton.LeftButton)
    assert BackupProfileModel.get_or_none(name='Test Profile') is not None
    assert main.profileSelector.currentItem().text() == 'Test Profile'

    # delete the new profile and ensure it is no longer available.
    mocker.patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes)
    qtbot.mouseClick(main.profileDeleteButton, QtCore.Qt.MouseButton.LeftButton)
    assert BackupProfileModel.get_or_none(name='Test Profile') is None
    assert main.profileSelector.currentItem().text() == 'Default'

    # attempt to delete the last remaining profile
    # see that it cannot be deleted, a warning is displayed, and the profile remains
    warning = mocker.patch.object(QToolTip, 'showText')
    qtbot.mouseClick(main.profileDeleteButton, QtCore.Qt.MouseButton.LeftButton)
    assert "Cannot delete the last profile." in warning.call_args[0][1]
    assert BackupProfileModel.get_or_none(name='Default') is not None
    assert main.profileSelector.currentItem().text() == 'Default'


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
    assert main.profileSelector.currentItem().text() == 'Test Profile'


def test_profile_import_no_duplicate_sources(qapp, qtbot, mocker):
    """Tests importing an existing profile and choosing to overwrite does not add duplicate sources."""
    main = qapp.main_window

    # Create a new profile and add sources
    profile = BackupProfileModel.create(name='Test Profile')
    sources = ['/path/to/source1', '/path/to/source2']
    for source_path in sources:
        SourceFileModel.create(dir=source_path, path=source_path, profile=profile)

    # Export the profile
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
        temp_file_path = temp_file.name

    export_window = ExportWindow(profile)
    mocker.patch.object(QFileDialog, 'getSaveFileName', return_value=(temp_file_path, 'JSON (*.json)'))
    export_window.run()

    # Mock the QMessageBox to return 'Yes' to overwrite the profile
    mocker.patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes)

    # Mock the QFileDialog to return the name of the temporary file
    mocker.patch.object(QFileDialog, 'getOpenFileName', return_value=(temp_file_path, 'JSON (*.json)'))

    # Import the profile and choose to overwrite
    main.profile_import_action()

    # Check that the sources in the profile are the same as before and that there are no duplicates
    imported_sources = [source.dir for source in SourceFileModel.select().where(SourceFileModel.profile == profile)]
    assert set(imported_sources) == set(sources)
    assert len(imported_sources) == len(sources)
