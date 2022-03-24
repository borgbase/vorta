import pytest

import vorta.views


def test_add_folder(qapp, qtbot, mocker, monkeypatch, choose_file_dialog):
    monkeypatch.setattr(
        vorta.views.source_tab, "choose_file_dialog", choose_file_dialog
    )
    main = qapp.main_window
    main.tabWidget.setCurrentIndex(1)
    tab = main.sourceTab

    tab.source_add(want_folder=True)
    qtbot.waitUntil(lambda: tab.sourceFilesWidget.rowCount() == 2, **pytest._wait_defaults)

    # Test paste button with mocked clipboard
    mock_clipboard = mocker.Mock()
    mock_clipboard.text.return_value = __file__
    mocker.patch.object(vorta.views.source_tab.QApplication, 'clipboard', return_value=mock_clipboard)
    tab.paste_text()
    qtbot.waitUntil(lambda: tab.sourceFilesWidget.rowCount() == 3, **pytest._wait_defaults)

    # Wait for directory sizing to finish
    qtbot.waitUntil(lambda: len(qapp.main_window.sourceTab.updateThreads) == 0, **pytest._wait_defaults)
