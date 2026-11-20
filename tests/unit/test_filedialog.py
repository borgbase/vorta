from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import QDir, QModelIndex
from PyQt6.QtWidgets import QMessageBox

from vorta.filedialog import VortaFileDialog, VortaFileSelector, get_drives_path


@pytest.fixture
def file_dialog(qapp):
    dialog = VortaFileDialog()
    yield dialog
    dialog.close()


def test_dialog_initial_state(file_dialog):
    """Verify the dialog initializes with correct defaults."""
    assert file_dialog.windowTitle() == "Vorta File Dialog"
    assert file_dialog.path_bar.text() == QDir.homePath()
    assert file_dialog.tree.model() == file_dialog.model
    assert file_dialog.tree.rootIndex() == file_dialog.model.index(QDir.homePath())


def test_selected_paths_with_access(file_dialog, mocker):
    """Test path selection when read access is granted."""
    mock_index = mocker.MagicMock()
    mock_index.column.return_value = 0
    mock_selection = mocker.MagicMock()
    mock_selection.selectedIndexes.return_value = [mock_index]

    with (
        patch.object(file_dialog.tree, 'selectionModel', return_value=mock_selection),
        patch.object(file_dialog.model, 'filePath', return_value="/valid/path"),
        patch('os.access', return_value=True),
    ):
        result = file_dialog.selected_paths()
        assert result == ["/valid/path"]


def test_selected_paths_without_access(file_dialog, mocker):
    """Test path selection when read access is denied."""
    mock_index = mocker.MagicMock(spec=QModelIndex)
    mock_index.column.return_value = 0
    mock_selection = mocker.MagicMock()
    mock_selection.selectedIndexes.return_value = [mock_index]

    with (
        patch.object(file_dialog.tree, 'selectionModel', return_value=mock_selection),
        patch.object(file_dialog.model, 'filePath', return_value="/no/access"),
        patch('os.access', return_value=False),
        patch('vorta.filedialog.QMessageBox') as MockQMessageBox,
    ):
        # mocking entire QMessageBox as msg.exec() was causing race conditions
        mock_msg = MockQMessageBox.return_value
        mock_msg.exec.return_value = QMessageBox.StandardButton.Ok

        result = file_dialog.selected_paths()

        assert result == []
        MockQMessageBox.assert_called_once()
        mock_msg.exec.assert_called_once()


def test_path_changed_valid(file_dialog, qtbot):
    """Test path bar updates with a valid path."""
    test_path = QDir.homePath()

    with patch('os.path.exists', return_value=True):
        file_dialog.path_bar.setText(test_path)
        qtbot.waitUntil(lambda: file_dialog.path_bar.styleSheet() == "")

        assert file_dialog.tree.rootIndex() == file_dialog.model.index(test_path)


def test_path_changed_invalid(file_dialog, qtbot):
    """Test path bar updates with an invalid path."""
    with patch('os.path.exists', return_value=False):
        file_dialog.path_bar.setText("/invalid/path")
        qtbot.waitUntil(lambda: file_dialog.path_bar.styleSheet() == "background-color: #ffcccc")


@pytest.mark.parametrize(
    'platform, existing, expected',
    [
        ('darwin', {'/Volumes'}, '/Volumes'),
        ('linux', {'/run/media/alice', '/media', '/mnt'}, '/run/media/alice'),
        ('linux', {'/media/alice', '/media', '/mnt'}, '/media/alice'),
        ('linux', {'/mnt'}, '/mnt'),
        ('linux', set(), None),
    ],
)
def test_get_drives_path(mocker, platform, existing, expected):
    """The drives folder is /Volumes on macOS and the first mount folder that exists elsewhere."""
    mocker.patch('vorta.filedialog.sys.platform', platform)
    mocker.patch('vorta.filedialog.getpass.getuser', return_value='alice')
    mocker.patch('vorta.filedialog.os.path.isdir', side_effect=lambda path: path in existing)
    assert get_drives_path() == expected


def test_go_drives(file_dialog, mocker):
    """The drives button opens the folder where external drives are mounted."""
    mocker.patch('vorta.filedialog.get_drives_path', return_value='/Volumes')
    mocker.patch('os.path.exists', return_value=True)
    file_dialog.btnDrives.click()
    assert file_dialog.path_bar.text() == '/Volumes'


def test_drives_button_hidden_without_drives_folder(qapp, mocker):
    """Without a mount folder there is nothing to open, so the button is hidden."""
    mocker.patch('vorta.filedialog.get_drives_path', return_value=None)
    dialog = VortaFileDialog()
    assert dialog.btnDrives.isHidden()
    dialog.close()


def test_file_selector_get_paths(mocker):
    """Test the instance selector method with successful selection."""
    mock_dialog = mocker.patch('vorta.filedialog.VortaFileDialog')
    mock_instance = mock_dialog.return_value
    mock_instance.exec.return_value = True
    mock_instance.selected_paths.return_value = ["/test/path"]

    selector = VortaFileSelector()
    paths = selector.get_paths()
    assert paths == ["/test/path"]


def test_file_selector_cancel(mocker):
    """Test the instance selector method when cancelled."""
    mock_dialog = mocker.patch('vorta.filedialog.VortaFileDialog')
    mock_instance = mock_dialog.return_value
    mock_instance.exec.return_value = False

    selector = VortaFileSelector()
    paths = selector.get_paths()
    assert paths == []
