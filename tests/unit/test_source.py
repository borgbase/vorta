import pytest
import vorta.views
from PyQt6.QtWidgets import QMessageBox


def test_source_add_remove(qapp, qtbot, monkeypatch, choose_file_dialog):
    monkeypatch.setattr(vorta.views.source_tab, "choose_file_dialog", choose_file_dialog)
    main = qapp.main_window
    main.tabWidget.setCurrentIndex(1)
    tab = main.sourceTab

    # test adding a folder
    tab.source_add(want_folder=True)
    qtbot.waitUntil(lambda: tab.sourceFilesWidget.rowCount() == 2, **pytest._wait_defaults)

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
def test_paste_text(qapp, qtbot, mocker, monkeypatch, choose_file_dialog, path, valid):
    monkeypatch.setattr(vorta.views.source_tab, "choose_file_dialog", choose_file_dialog)
    main = qapp.main_window
    main.tabWidget.setCurrentIndex(1)
    tab = main.sourceTab

    mock_clipboard = mocker.Mock()
    mock_clipboard.text.return_value = path
    mocker.patch.object(vorta.views.source_tab.QApplication, 'clipboard', return_value=mock_clipboard)
    monkeypatch.setattr(QMessageBox, "exec", lambda *args: True)
    tab.paste_text()
    if valid:
        assert not hasattr(tab, '_msg')
        qtbot.waitUntil(lambda: tab.sourceFilesWidget.rowCount() == 2, **pytest._wait_defaults)
        # Wait for directory sizing to finish
        qtbot.waitUntil(lambda: len(qapp.main_window.sourceTab.updateThreads) == 0, **pytest._wait_defaults)
    else:
        qtbot.waitUntil(lambda: hasattr(tab, "_msg"), **pytest._wait_defaults)
        assert tab._msg.text().startswith("Some of your sources are invalid")
