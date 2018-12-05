import logging
from PyQt5 import QtCore
import vorta.models
import vorta.views


def test_add_folder(app, qtbot, tmpdir, monkeypatch, choose_file_dialog):
    monkeypatch.setattr(
        vorta.views.source_tab, "choose_file_dialog", choose_file_dialog
    )
    main = app.main_window
    main.tabWidget.setCurrentIndex(1)
    tab = main.sourceTab

    qtbot.mouseClick(tab.sourceAddFolder, QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: tab.sourceFilesWidget.count() == 2)

    for src in vorta.models.SourceFileModel.select():
        logging.error(src.dir, src.profile)
