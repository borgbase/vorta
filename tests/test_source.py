from PyQt5 import QtCore
import vorta.models
import vorta.views


def test_add_folder(qapp, qtbot, tmpdir, monkeypatch, choose_file_dialog):
    monkeypatch.setattr(
        vorta.views.source_tab, "choose_file_dialog", choose_file_dialog
    )
    main = qapp.main_window
    main.tabWidget.setCurrentIndex(1)
    tab = main.sourceTab

    qtbot.mouseClick(tab.sourceAddFolder, QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: tab.sourceFilesWidget.count() == 2, timeout=5000)
