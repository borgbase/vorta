import logging
from PyQt5 import QtCore
import vorta.models


def test_add_folder(app, qtbot, tmpdir):
    main = app.main_window
    main.tabWidget.setCurrentIndex(1)
    tab = main.sourceTab

    qtbot.mouseClick(tab.sourceAddFolder, QtCore.Qt.LeftButton)

    qtbot.waitUntil(lambda: len(tab._file_dialog.selectedFiles()) > 0, timeout=3000)
    tab._file_dialog.accept()

    qtbot.waitUntil(lambda: tab.sourceDirectoriesWidget.count() == 2)

    for src in vorta.models.SourceDirModel.select():
        logging.error(src.dir, src.profile)
