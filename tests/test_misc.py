from PyQt5 import QtCore
from PyQt5.QtWidgets import QCheckBox
from pathlib import Path
import pytest
import sys


@pytest.mark.skipif(sys.platform != 'linux', reason="Autostart files only generated in Linux")
def test_autostart(qapp, qtbot):
    main = qapp.main_window
    main.tabWidget.setCurrentIndex(4)
    tab = main.miscTab

    for x in range(0, tab.checkboxLayout.count()):
        checkbox = tab.checkboxLayout.itemAt(x).widget()
        checkbox.__class__ = QCheckBox
        if checkbox.text().startswith("Automatically"):
            if checkbox.isChecked():
                qtbot.mouseClick(checkbox, QtCore.Qt.LeftButton)
            qtbot.mouseClick(checkbox, QtCore.Qt.LeftButton)
            break

    autostart_path = Path.home() / ".config" / "autostart" / "vorta.desktop"
    assert(autostart_path.exists())

    with open(autostart_path) as desktop_file:
        desktop_file_text = desktop_file.read()

        assert(desktop_file_text.startswith("[Desktop Entry]"))
