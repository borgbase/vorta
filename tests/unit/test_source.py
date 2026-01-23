import os

import pytest
from PyQt6 import QtCore
from PyQt6.QtWidgets import QMessageBox
from test_constants import TEST_TEMP_DIR


@pytest.fixture()
def source_env(qapp, qtbot):
    """Handles setup and teardown for source tab tests."""
    main = qapp.main_window

    main.show()
    qtbot.waitUntil(main.isVisible, **pytest._wait_defaults)

    main.tabWidget.setCurrentIndex(1)  # activate source tab
    tab = main.sourceTab

    qtbot.waitUntil(tab.isVisible, **pytest._wait_defaults)  # wait for the tab
    qtbot.waitUntil(lambda: tab.sourceFilesWidget.rowCount() >= 0, **pytest._wait_defaults)
    yield main, tab

    qapp.processEvents()  # cleanup


@pytest.mark.skip(reason="prone to failure due to background thread")
def test_source_add_remove(qapp, qtbot, mocker, source_env):
    main, tab = source_env
    qtbot.waitUntil(tab.isVisible, **pytest._wait_defaults)  # visibility check

    mocker.patch.object(QMessageBox, "exec")
    mocker.patch('vorta.filedialog.VortaFileSelector.get_paths', return_value=[os.path.join(TEST_TEMP_DIR, 'test')])
    mocker.patch('os.access', return_value=True)

    initial_count = tab.sourceFilesWidget.rowCount()

    # test add
    tab.source_add()
    qtbot.waitUntil(lambda: tab.sourceFilesWidget.rowCount() > initial_count, **pytest._wait_defaults)

    # test remove
    tab.sourceFilesWidget.selectRow(initial_count)  # Select the new row
    qtbot.mouseClick(tab.removeButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: tab.sourceFilesWidget.rowCount() == initial_count, **pytest._wait_defaults)


@pytest.mark.skip(reason="prone to failure due to background thread")
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
    mocker.patch('os.access', return_value=True)
    mocker.patch(
        'vorta.filedialog.VortaFileSelector.get_paths',
        return_value=[TEST_TEMP_DIR, os.path.join(TEST_TEMP_DIR, 'another')],
    )
    tab.source_add()
    qtbot.waitUntil(lambda: tab.sourceFilesWidget.rowCount() == 2, **pytest._wait_defaults)
    update_path_info_spy.reset_mock()

    # retest that `update_path_info()` has been called for each source path
    qtbot.mouseClick(tab.updateButton, QtCore.Qt.MouseButton.LeftButton)
    assert tab.sourceFilesWidget.rowCount() == 2
    assert update_path_info_spy.call_count == 2


@pytest.mark.skip(reason="prone to failure due to background thread")
def test_source_copy(qapp, qtbot, mocker, source_env):
    main, tab = source_env
    qtbot.waitUntil(tab.isVisible, **pytest._wait_defaults)

    mock_clipboard = mocker.patch.object(qapp.clipboard(), "setMimeData")
    mocker.patch('os.access', return_value=True)
    mocker.patch('vorta.filedialog.VortaFileSelector.get_paths', return_value=[TEST_TEMP_DIR])

    initial_count = tab.sourceFilesWidget.rowCount()
    tab.source_add()
    qtbot.waitUntil(lambda: tab.sourceFilesWidget.rowCount() > initial_count, **pytest._wait_defaults)

    tab.sourceFilesWidget.selectRow(initial_count)
    tab.source_copy()
    assert mock_clipboard.call_count == 1


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
#         qtbot.waitUntil(lambda: tab.sourceFilesWidget.rowCount() == 2, **pytest._wait_defaults)
#         assert tab.sourceFilesWidget.rowCount() == 2
#     else:
#         qtbot.waitUntil(lambda: hasattr(tab, "_msg"), **pytest._wait_defaults)
#         assert tab._msg.text().startswith("Some of your sources are invalid")
#         assert tab.sourceFilesWidget.rowCount() == 1
