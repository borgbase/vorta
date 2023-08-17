import pytest
import vorta.views
from PyQt6 import QtCore
from PyQt6.QtWidgets import QMessageBox
from vorta.views.main_window import MainWindow
from vorta.views.source_tab import SourceTab


@pytest.fixture()
def source_env(qapp, qtbot, monkeypatch, choose_file_dialog):
    """
    Handles common setup and teardown for unit tests involving the source tab.
    """
    main: MainWindow = qapp.main_window
    tab: SourceTab = main.sourceTab
    main.tabWidget.setCurrentIndex(1)
    qtbot.waitUntil(lambda: tab.sourceFilesWidget.rowCount() == 1, timeout=2000)
    monkeypatch.setattr(vorta.views.source_tab, "choose_file_dialog", choose_file_dialog)

    yield main, tab

    # Wait for directory sizing to finish
    qtbot.waitUntil(lambda: len(qapp.main_window.sourceTab.updateThreads) == 0, timeout=2000)


def test_source_add_remove(qapp, qtbot, monkeypatch, mocker, source_env):
    """
    Tests adding and removing source to ensure expected behavior.
    """
    main, tab = source_env
    mocker.patch.object(QMessageBox, "exec")  # prevent QMessageBox from stopping test

    # test adding a folder with os access
    mocker.patch('os.access', return_value=True)
    tab.source_add(want_folder=True)
    qtbot.waitUntil(lambda: tab.sourceFilesWidget.rowCount() == 2, **pytest._wait_defaults)
    assert tab.sourceFilesWidget.rowCount() == 2

    # test adding a folder without os access
    mocker.patch('os.access', return_value=False)
    tab.source_add(want_folder=True)
    assert tab.sourceFilesWidget.rowCount() == 2

    # test removing a folder
    tab.sourceFilesWidget.selectRow(1)
    qtbot.mouseClick(tab.removeButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: tab.sourceFilesWidget.rowCount() == 1, **pytest._wait_defaults)
    assert tab.sourceFilesWidget.rowCount() == 1


@pytest.mark.parametrize(
    "path, valid",
    [
        (__file__, True),  # valid path
        ("test", False),  # invalid path
        (f"file://{__file__}", True),  # valid - normal path with prefix that will be stripped
        (f"file://{__file__}\n{__file__}", True),  # valid - two files separated by new line
        (f"file://{__file__}{__file__}", False),  # invalid - no new line separating file names
    ],
)
def test_valid_and_invalid_source_paths(qapp, qtbot, mocker, source_env, path, valid):
    """
    Valid paths will be added as a source.
    Invalid paths will trigger an alert and not be added as a source.
    """
    main, tab = source_env
    mock_clipboard = mocker.Mock()
    mock_clipboard.text.return_value = path

    mocker.patch.object(vorta.views.source_tab.QApplication, 'clipboard', return_value=mock_clipboard)
    mocker.patch.object(QMessageBox, "exec")  # prevent QMessageBox from stopping test
    tab.paste_text()

    if valid:
        assert not hasattr(tab, '_msg')
        qtbot.waitUntil(lambda: tab.sourceFilesWidget.rowCount() == 2, **pytest._wait_defaults)
        assert tab.sourceFilesWidget.rowCount() == 2
    else:
        qtbot.waitUntil(lambda: hasattr(tab, "_msg"), **pytest._wait_defaults)
        assert tab._msg.text().startswith("Some of your sources are invalid")
        assert tab.sourceFilesWidget.rowCount() == 1


def test_sources_update(qapp, qtbot, mocker, source_env):
    """
    Tests the source update button in the source tab
    """
    main, tab = source_env
    update_path_info_spy = mocker.spy(tab, "update_path_info")

    # test that `update_path_info()` has been called for each source path
    qtbot.mouseClick(tab.updateButton, QtCore.Qt.MouseButton.LeftButton)
    assert tab.sourceFilesWidget.rowCount() == 1
    assert update_path_info_spy.call_count == 1

    # add a new source and reset mock
    tab.source_add(want_folder=True)
    qtbot.waitUntil(lambda: tab.sourceFilesWidget.rowCount() == 2, **pytest._wait_defaults)
    update_path_info_spy.reset_mock()

    # retest that `update_path_info()` has been called for each source path
    qtbot.mouseClick(tab.updateButton, QtCore.Qt.MouseButton.LeftButton)
    assert tab.sourceFilesWidget.rowCount() == 2
    assert update_path_info_spy.call_count == 2


def test_source_copy(qapp, qtbot, monkeypatch, mocker, source_env):
    """
    Test source_copy() with and without an index passed.
    If no index is passed, it should copy the first selected source
    """
    main, tab = source_env

    mock_clipboard = mocker.patch.object(qapp.clipboard(), "setMimeData")
    tab.source_add(want_folder=True)
    qtbot.waitUntil(lambda: tab.sourceFilesWidget.rowCount() == 2, **pytest._wait_defaults)

    tab.sourceFilesWidget.selectRow(0)
    tab.source_copy()
    assert mock_clipboard.call_count == 1
    source = mock_clipboard.call_args[0][0]  # retrieves the QMimeData() object used in method call
    assert source.text() == "/tmp"

    index = tab.sourceFilesWidget.model().index(1, 0)
    tab.source_copy(index)
    assert mock_clipboard.call_count == 2
    source = mock_clipboard.call_args[0][0]  # retrieves the QMimeData() object used in method call
    assert source.text() == "/tmp/another"
