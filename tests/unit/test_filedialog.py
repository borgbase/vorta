from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import QDir, QModelIndex
from PyQt6.QtWidgets import QMessageBox

from vorta.filedialog import VortaFileDialog, VortaFileSelector


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
