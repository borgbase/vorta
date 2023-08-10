import pytest
import vorta.views
from PyQt6 import QtCore
from PyQt6.QtWidgets import QMessageBox


@pytest.fixture()
def source_env(qapp, qtbot, monkeypatch, choose_file_dialog):
    def setup():
        monkeypatch.setattr(vorta.views.source_tab, "choose_file_dialog", choose_file_dialog)
        main = qapp.main_window
        main.tabWidget.setCurrentIndex(1)
        tab = main.sourceTab
        qtbot.waitUntil(lambda: tab.sourceFilesWidget.rowCount() == 1, timeout=2000)
        return main, tab

    main, tab = setup()
    yield main, tab

    # Wait for directory sizing to finish
    qtbot.waitUntil(lambda: len(qapp.main_window.sourceTab.updateThreads) == 0, timeout=2000)


def test_source_add_remove(qapp, qtbot, monkeypatch, mocker, source_env):
    main, tab = source_env
    # test adding a folder with os access
    mocker.patch('os.access', return_value=True)
    tab.source_add(want_folder=True)
    qtbot.waitUntil(lambda: tab.sourceFilesWidget.rowCount() == 2, **pytest._wait_defaults)
    assert tab.sourceFilesWidget.rowCount() == 2

    # test adding a folder without os access
    mocker.patch('os.access', return_value=False)
    monkeypatch.setattr(QMessageBox, "exec", lambda *args: True)  # prevent QMessageBox from stopping test
    tab.source_add(want_folder=True)
    assert tab.sourceFilesWidget.rowCount() == 2

    # test removing a folder
    tab.sourceFilesWidget.selectRow(1)
    tab.source_remove()
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
def test_paste_text(qapp, qtbot, mocker, monkeypatch, source_env, path, valid):
    main, tab = source_env
    mock_clipboard = mocker.Mock()
    mock_clipboard.text.return_value = path

    mocker.patch.object(vorta.views.source_tab.QApplication, 'clipboard', return_value=mock_clipboard)
    monkeypatch.setattr(QMessageBox, "exec", lambda *args: True)  # prevent QMessageBox from stopping test
    tab.paste_text()

    if valid:
        # valid paths will be added as a source
        assert not hasattr(tab, '_msg')
        qtbot.waitUntil(lambda: tab.sourceFilesWidget.rowCount() == 2, **pytest._wait_defaults)
        assert tab.sourceFilesWidget.rowCount() == 2
    else:
        # invalid paths will trigger an alert and not be added as a source
        qtbot.waitUntil(lambda: hasattr(tab, "_msg"), **pytest._wait_defaults)
        assert tab._msg.text().startswith("Some of your sources are invalid")
        assert tab.sourceFilesWidget.rowCount() == 1


def test_sources_update(qapp, qtbot, mocker, source_env):
    main, tab = source_env

    # test that `update_path_info()` has been called for each source path
    update_path_info_spy = mocker.spy(tab, "update_path_info")
    qtbot.mouseClick(tab.updateButton, QtCore.Qt.MouseButton.LeftButton)
    assert tab.sourceFilesWidget.rowCount() == 1
    assert update_path_info_spy.call_count == 1

    # add a new source and test again
    tab.source_add(want_folder=True)
    qtbot.mouseClick(tab.updateButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: tab.sourceFilesWidget.rowCount() == 2, **pytest._wait_defaults)
    update_path_info_spy.reset_mock()
    tab.sources_update()
    assert tab.sourceFilesWidget.rowCount() == 2
    assert update_path_info_spy.call_count == 2
