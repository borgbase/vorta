from PyQt5 import QtCore
from PyQt5.QtWidgets import QCheckBox
from pathlib import Path
import pytest
import os
import sys


@pytest.mark.skipif(sys.platform != 'linux', reason="Autostart files only generated in Linux")
def test_linux_autostart(qapp, qtbot):
    main = qapp.main_window
    main.tabWidget.setCurrentIndex(4)
    tab = main.miscTab

    for x in range(0, tab.checkboxLayout.count()):
        checkbox = tab.checkboxLayout.itemAt(x).widget()
        checkbox.__class__ = QCheckBox
        if checkbox.text().startswith("Automatically"):
            # Have to use pos to click checkbox correctly
            # https://stackoverflow.com/questions/19418125/pysides-qtest-not-checking-box/24070484#24070484
            qtbot.mouseClick(checkbox, QtCore.Qt.LeftButton, pos=QtCore.QPoint(2, checkbox.height() / 2))
            break

    autostart_path = Path(os.environ.get(
        "XDG_CONFIG_HOME", os.path.expanduser("~") + '/.config') + "/autostart") / "vorta.desktop"
    qtbot.waitUntil(lambda: autostart_path.exists(), timeout=5000)

    with open(autostart_path) as desktop_file:
        desktop_file_text = desktop_file.read()

        assert(desktop_file_text.startswith("[Desktop Entry]"))
