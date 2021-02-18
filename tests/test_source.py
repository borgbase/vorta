import os
import pytest
import vorta.models
import vorta.views
from PyQt5.QtWidgets import QApplication
from PyQt5 import QtCore


def test_add_folder(qapp, qtbot, tmpdir, monkeypatch, choose_file_dialog):
    monkeypatch.setattr(
        vorta.views.source_tab, "choose_file_dialog", choose_file_dialog
    )
    main = qapp.main_window
    main.tabWidget.setCurrentIndex(1)
    tab = main.sourceTab

    tab.sourceAddFolder.click()
    qtbot.waitUntil(lambda: tab.sourceFilesWidget.rowCount() == 2, **pytest._wait_defaults)

    # Test paste button
    QApplication.clipboard().setText(os.path.expanduser('~'))  # Load clipboard
    qtbot.mouseClick(tab.paste, QtCore.Qt.LeftButton)
    assert tab.sourceFilesWidget.rowCount() == 3
