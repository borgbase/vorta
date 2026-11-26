import os
import sys
import threading

import pytest
from PyQt6 import QtCore
from PyQt6.QtWidgets import QLineEdit, QMessageBox
from test_constants import TEST_SOURCE_DIR, TEST_TEMP_DIR

from vorta.store.models import BackupProfileModel, SourceFileModel
from vorta.utils import FilePathInfoAsync
from vorta.views.partials.source_files_table_model import SourceFilesModel


@pytest.fixture()
def source_env(qapp, qtbot):
    """Handles setup and teardown for source tab tests."""
    main = qapp.main_window

    main.show()
    qtbot.waitUntil(main.isVisible, **pytest._wait_defaults)

    main.tabWidget.setCurrentIndex(1)  # activate source tab
    tab = main.sourceTab

    qtbot.waitUntil(tab.isVisible, **pytest._wait_defaults)  # wait for the tab
    qtbot.waitUntil(lambda: tab.sourceFilesWidget.model().rowCount() >= 0, **pytest._wait_defaults)
    yield main, tab

    for thrd in list(tab.updateThreads):
        thrd.cancel()
    qtbot.waitUntil(lambda: not tab.updateThreads, **pytest._wait_defaults)
    qapp.processEvents()  # cleanup


def gated_path_info(gate):
    """A FilePathInfoAsync that delivers its result at once, then keeps running until ``gate`` is set."""

    class GatedPathInfo(FilePathInfoAsync):
        def run(self):
            self.signal.emit(self.path, '1', '1')
            gate.wait(timeout=20)

    return GatedPathInfo


@pytest.mark.skip(reason="prone to failure due to background thread")
def test_source_add_remove(qapp, qtbot, mocker, source_env):
    main, tab = source_env
    qtbot.waitUntil(tab.isVisible, **pytest._wait_defaults)  # visibility check

    mocker.patch.object(QMessageBox, "exec")
    mocker.patch('vorta.filedialog.VortaFileSelector.get_paths', return_value=[os.path.join(TEST_TEMP_DIR, 'test')])
    mocker.patch('os.access', return_value=True)

    initial_count = tab.sourceFilesWidget.model().rowCount()

    # test add
    tab.source_add()
    qtbot.waitUntil(lambda: tab.sourceFilesWidget.model().rowCount() > initial_count, **pytest._wait_defaults)

    # test remove
    tab.sourceFilesWidget.selectRow(initial_count)  # Select the new row
    qtbot.mouseClick(tab.removeButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: tab.sourceFilesWidget.model().rowCount() == initial_count, **pytest._wait_defaults)


@pytest.mark.skip(reason="prone to failure due to background thread")
def test_sources_update(qapp, qtbot, mocker, source_env):
    """
    Tests the source update button in the source tab
    """
    main, tab = source_env
    update_path_info_spy = mocker.spy(tab, "update_path_info")

    # test that `update_path_info()` has been called for each source path
    qtbot.mouseClick(tab.updateButton, QtCore.Qt.MouseButton.LeftButton)
    assert tab.sourceFilesWidget.model().rowCount() == 1
    assert update_path_info_spy.call_count == 1

    # add a new source and reset mock
    mocker.patch('os.access', return_value=True)
    mocker.patch(
        'vorta.filedialog.VortaFileSelector.get_paths',
        return_value=[TEST_TEMP_DIR, os.path.join(TEST_TEMP_DIR, 'another')],
    )
    tab.source_add()
    qtbot.waitUntil(lambda: tab.sourceFilesWidget.model().rowCount() == 2, **pytest._wait_defaults)
    update_path_info_spy.reset_mock()

    # retest that `update_path_info()` has been called for each source path
    qtbot.mouseClick(tab.updateButton, QtCore.Qt.MouseButton.LeftButton)
    assert tab.sourceFilesWidget.model().rowCount() == 2
    assert update_path_info_spy.call_count == 2


@pytest.mark.skip(reason="prone to failure due to background thread")
def test_source_copy(qapp, qtbot, mocker, source_env):
    main, tab = source_env
    qtbot.waitUntil(tab.isVisible, **pytest._wait_defaults)

    mock_clipboard = mocker.patch.object(qapp.clipboard(), "setMimeData")
    mocker.patch('os.access', return_value=True)
    mocker.patch('vorta.filedialog.VortaFileSelector.get_paths', return_value=[TEST_TEMP_DIR])

    initial_count = tab.sourceFilesWidget.model().rowCount()
    tab.source_add()
    qtbot.waitUntil(lambda: tab.sourceFilesWidget.model().rowCount() > initial_count, **pytest._wait_defaults)

    tab.sourceFilesWidget.selectRow(initial_count)
    tab.source_copy()
    assert mock_clipboard.call_count == 1


def test_source_remove_under_sort(qapp, qtbot, source_env):
    """Removing the first visual row after sorting deletes the correct DB record (proxy mapToSource)."""
    main, tab = source_env
    profile = tab.profile()

    SourceFileModel.delete().where(SourceFileModel.profile == profile).execute()
    small = SourceFileModel.create(dir='/vorta/small', profile=profile, dir_size=1024, path_isdir=True)
    big = SourceFileModel.create(dir='/vorta/big', profile=profile, dir_size=8 * 1024**3, path_isdir=True)
    tab.populate_from_profile()
    assert tab.sourceFilesWidget.model().rowCount() == 2

    # Sort by size descending → the largest source is visual row 0.
    tab.source_proxy.sort(SourceFilesModel.COL_SIZE, QtCore.Qt.SortOrder.DescendingOrder)
    tab.sourceFilesWidget.selectRow(0)

    tab.source_remove()

    assert SourceFileModel.get_or_none(id=big.id) is None
    assert SourceFileModel.get_or_none(id=small.id) is not None


@pytest.mark.parametrize(
    'key', [QtCore.Qt.Key.Key_Delete] + ([QtCore.Qt.Key.Key_Backspace] if sys.platform == 'darwin' else [])
)
def test_source_remove_shortcut(qapp, qtbot, mocker, source_env, key):
    main, tab = source_env
    profile = tab.profile()
    SourceFileModel.delete().where(SourceFileModel.profile == profile).execute()
    small = SourceFileModel.create(dir='/vorta/small', profile=profile, dir_size=1024, path_isdir=True)
    big = SourceFileModel.create(dir='/vorta/big', profile=profile, dir_size=8 * 1024**3, path_isdir=True)
    biggest = SourceFileModel.create(dir='/vorta/biggest', profile=profile, dir_size=16 * 1024**3, path_isdir=True)
    tab.populate_from_profile()
    tab.source_proxy.sort(SourceFilesModel.COL_SIZE, QtCore.Qt.SortOrder.DescendingOrder)
    selection = tab.sourceFilesWidget.selectionModel()
    for row in (0, 1):
        selection.select(
            tab.source_proxy.index(row, 0),
            QtCore.QItemSelectionModel.SelectionFlag.Select | QtCore.QItemSelectionModel.SelectionFlag.Rows,
        )
    qapp.setActiveWindow(main)
    tab.sourceFilesWidget.setFocus()
    qapp.processEvents()
    assert tab.sourceFilesWidget.hasFocus()
    warning = mocker.patch.object(QMessageBox, 'question')

    qtbot.keyClick(tab.sourceFilesWidget, key)

    assert SourceFileModel.get_or_none(id=big.id) is None
    assert SourceFileModel.get_or_none(id=biggest.id) is None
    assert SourceFileModel.get_or_none(id=small.id) is not None
    assert BackupProfileModel.select().count() == 1
    warning.assert_not_called()

    tab.sourceFilesWidget.clearSelection()
    qtbot.keyClick(tab.sourceFilesWidget, key)
    assert SourceFileModel.get_or_none(id=small.id) is not None


def test_delete_shortcuts_leave_text_editing_alone(qapp, qtbot, mocker, source_env):
    main, tab = source_env
    BackupProfileModel.create(name='Test Profile')
    main.populate_profile_selector()
    tab.sourceFilesWidget.selectRow(0)
    source_count = SourceFileModel.select().count()
    editor = QLineEdit('abc', main)
    editor.show()
    qapp.setActiveWindow(main)
    editor.setFocus()
    editor.setCursorPosition(1)
    qapp.processEvents()
    question = mocker.patch.object(QMessageBox, 'question')

    qtbot.keyClick(editor, QtCore.Qt.Key.Key_Delete)
    qtbot.keyClick(editor, QtCore.Qt.Key.Key_Backspace)

    assert editor.text() == 'c'
    assert SourceFileModel.select().count() == source_count
    assert BackupProfileModel.select().count() == 2
    question.assert_not_called()
    editor.deleteLater()


def test_path_info_thread_kept_until_finished(qapp, qtbot, mocker, source_env):
    """The worker stays referenced after its result arrives, until it has finished (#2614)."""
    main, tab = source_env
    gate = threading.Event()
    mocker.patch('vorta.views.source_tab.FilePathInfoAsync', gated_path_info(gate))
    try:
        path = TEST_SOURCE_DIR
        tab.update_path_info(path)
        thrd = tab.updateThreads[0]
        qtbot.waitUntil(lambda: path not in tab.source_model._calculating, **pytest._wait_defaults)

        assert thrd in tab.updateThreads
        assert thrd.isRunning()

        gate.set()
        qtbot.waitUntil(lambda: not tab.updateThreads, **pytest._wait_defaults)
        assert thrd.wait(5000)
    finally:
        gate.set()


def test_remove_running_path_info_then_readd(qapp, qtbot, mocker, source_env):
    """Removing a source cancels its running worker without dropping it; re-adding starts a new one (#2614)."""
    main, tab = source_env
    gate = threading.Event()
    mocker.patch('vorta.views.source_tab.FilePathInfoAsync', gated_path_info(gate))
    try:
        path = TEST_SOURCE_DIR
        assert tab.source_model.rowCount() == 1
        tab.update_path_info(path)
        thrd = tab.updateThreads[0]
        tab.sourceFilesWidget.selectRow(0)
        tab.source_remove()

        assert thrd in tab.updateThreads
        assert thrd.cancelled

        SourceFileModel.create(dir=path, profile=tab.profile())
        tab.populate_from_profile()
        tab.update_path_info(path)
        assert len(tab.updateThreads) == 2

        gate.set()
        qtbot.waitUntil(lambda: not tab.updateThreads, **pytest._wait_defaults)
    finally:
        gate.set()


# This test is for the paste_text() feature that was removed. Kept here for reference or possible future use.
# @pytest.mark.skip(reason="prone to failure due to background thread")
# @pytest.mark.parametrize(
#     "path, valid",
#     [
#         (__file__, True),  # valid path
#         ("test", False),  # invalid path
#         (f"file://{__file__}", True),  # valid - normal path with prefix that will be stripped
#         (f"file://{__file__}\n{__file__}", True),  # valid - two files separated by new line
#         (f"file://{__file__}{__file__}", False),  # invalid - no new line separating file names
#     ],
# )
# def test_valid_and_invalid_source_paths(qapp, qtbot, mocker, source_env, path, valid):
#     """
#     Valid paths will be added as a source.
#     Invalid paths will trigger an alert and not be added as a source.
#     """
#     main, tab = source_env
#     mock_clipboard = mocker.Mock()
#     mock_clipboard.text.return_value = path

#     mocker.patch.object(vorta.views.source_tab.QApplication, 'clipboard', return_value=mock_clipboard)
#     mocker.patch.object(QMessageBox, "exec")  # prevent QMessageBox from stopping test
#     tab.paste_text()

#     if valid:
#         assert not hasattr(tab, '_msg')
#         qtbot.waitUntil(lambda: tab.sourceFilesWidget.model().rowCount() == 2, **pytest._wait_defaults)
#         assert tab.sourceFilesWidget.model().rowCount() == 2
#     else:
#         qtbot.waitUntil(lambda: hasattr(tab, "_msg"), **pytest._wait_defaults)
#         assert tab._msg.text().startswith("Some of your sources are invalid")
#         assert tab.sourceFilesWidget.model().rowCount() == 1
