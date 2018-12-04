import logging
from PyQt5 import QtCore
import vorta.models
import vorta.views


def test_add_folder(app, qtbot, tmpdir, monkeypatch, choose_folder_dialog):
    monkeypatch.setattr(
        vorta.views.source_tab, "choose_folder_dialog", choose_folder_dialog
    )
    main = app.main_window
    main.tabWidget.setCurrentIndex(1)
    tab = main.sourceTab

    qtbot.mouseClick(tab.sourceAddFolder, QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: tab.sourceDirectoriesWidget.count() == 2)

    for src in vorta.models.SourceDirModel.select():
        logging.error(src.dir, src.profile)
