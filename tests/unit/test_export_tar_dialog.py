import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialogButtonBox

from vorta.store.models import BackupProfileModel
from vorta.views.export_tar_dialog import ExportTarDialog


def test_export_tar_dialog_init(qapp, qtbot, mocker):
    """Test dialog initialization and default state"""
    profile = mocker.MagicMock()
    profile.repo = mocker.MagicMock()
    profile.repo.id = 1

    dialog = ExportTarDialog(None, profile, "test_archive")
    qtbot.addWidget(dialog)

    assert dialog.archiveNameLabel.text() == "test_archive"
    assert dialog.comboCompression.currentText() == "none"
    assert dialog.spinStripComponents.value() == 0


def test_export_tar_dialog_compression_detection(qapp, qtbot, mocker):
    """Test auto-detection of compression from filename"""
    profile = mocker.MagicMock()

    dialog = ExportTarDialog(None, profile, "test_archive")
    qtbot.addWidget(dialog)

    # Mock file dialog to return a tar.gz file
    mocker.patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName', return_value=('/tmp/test.tar.gz', ''))

    # Trigger browse
    qtbot.mouseClick(dialog.btnBrowse, Qt.MouseButton.LeftButton)

    assert dialog.destinationInput.text() == '/tmp/test.tar.gz'
    assert dialog.comboCompression.currentText() == 'gzip'


def test_export_tar_dialog_job_creation(qapp, qtbot, mocker):
    """Test that accepting the dialog creates and submits the job"""

    # Setup profile mock
    profile = mocker.MagicMock()
    # Ensure profile.repo has an id attribute
    profile.repo = mocker.MagicMock()
    profile.repo.id = 1
    profile.repo.url = "test_repo"

    # Setup main window/app mock
    main_window = mocker.Mock(spec=ExportTarDialog)
    main_window.app = mocker.MagicMock()
    main_window.app.jobs_manager = mocker.MagicMock()

    dialog = ExportTarDialog(None, profile, "test_archive")
    dialog.main_window = main_window
    qtbot.addWidget(dialog)

    # Fill in required fields
    dialog.destinationInput.setText('/tmp/output.tar')

    # Mock BorgExportTar.prepare
    job_data_mock = {'ok': True, 'cmd': ['borg', 'export-tar', 'some_arg']}

    # We MUST patch the class in the module where it is IMPORTED (views.export_tar_dialog),
    # NOT where it is defined.
    # verify=True ensures we are patching the real class signature/structure if possible,
    # but since we are mocking the return value of a static method on the class mock,
    # and the instantiation... let's just use a standard patch.
    mock_job_class = mocker.patch('vorta.views.export_tar_dialog.BorgExportTar')
    mock_job_class.prepare.return_value = job_data_mock

    # Click OK
    dialog.buttonBox.button(QDialogButtonBox.StandardButton.Ok).click()

    # Debugging what happened
    print(f"\nMock call count: {mock_job_class.call_count}")
    if mock_job_class.call_count > 0:
        print(f"Mock call args: {mock_job_class.call_args}")

    # Verify job was created
    assert mock_job_class.call_count == 1

    # Analyze arguments passed to the constructor
    args, kwargs = mock_job_class.call_args
    # Expected call: BorgExportTar(cmd, params, site=...)
    # args[0] = cmd list
    # args[1] = params dict

    assert args[0] == job_data_mock['cmd']
    assert args[1] == job_data_mock
    assert kwargs.get('site') == 1

    # Verify job was added to manager
    # The return value of the class constructor is the instance
    mock_job_instance = mock_job_class.return_value
    main_window.app.jobs_manager.add_job.assert_called_once_with(mock_job_instance)


def test_export_tar_dialog_advanced_options(qapp, qtbot, mocker):
    """Test sending advanced options from UI."""
    profile = mocker.MagicMock()
    profile.repo = mocker.MagicMock()

    # Mock V2 to enable format
    mocker.patch('vorta.utils.borg_compat.check', return_value=True)

    dialog = ExportTarDialog(None, profile, "test_archive")
    qtbot.addWidget(dialog)

    # Fill UI
    dialog.destinationInput.setText('/tmp/output.tar')
    dialog.inputExcludes.setText("*.tmp cache")
    dialog.inputPaths.setText("home/user/docs")
    dialog.comboFormat.setCurrentText("PAX")

    # Mock prepare
    mock_prepare = mocker.patch(
        'vorta.views.export_tar_dialog.BorgExportTar.prepare', return_value={'ok': False}
    )  # return false so we don't proceed to job creation

    # Accept
    dialog.buttonBox.button(QDialogButtonBox.StandardButton.Ok).click()

    # Check prepare was called with correct args
    mock_prepare.assert_called_once()
    call_kwargs = mock_prepare.call_args[1]

    assert call_kwargs['excludes'] == ['*.tmp', 'cache']
    assert call_kwargs['paths'] == ['home/user/docs']
    assert call_kwargs['tar_format'] == 'PAX'
