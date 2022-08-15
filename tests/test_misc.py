import os
import sys
from pathlib import Path
import pytest
from PyQt5 import QtCore
from PyQt5.QtWidgets import QCheckBox, QFormLayout


def test_autostart(qapp, qtbot):
    '''Check if file exists only on Linux, otherwise just check it doesn't crash'''
    main = qapp.main_window
    main.tabWidget.setCurrentIndex(4)
    tab = main.miscTab

    def click_autostart():
        for x in range(0, tab.checkboxLayout.count()):
            item = tab.checkboxLayout.itemAt(x, QFormLayout.ItemRole.FieldRole)
            if not item:
                continue
            checkbox = item.widget()
            checkbox.__class__ = QCheckBox
            if checkbox.text().startswith("Automatically"):
                # Have to use pos to click checkbox correctly
                # https://stackoverflow.com/questions/19418125/pysides-qtest-not-checking-box/24070484#24070484
                qtbot.mouseClick(checkbox, QtCore.Qt.LeftButton, pos=QtCore.QPoint(2, int(checkbox.height() / 2)))
                break

    click_autostart()

    if sys.platform == 'linux':
        autostart_path = (
            Path(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~") + '/.config') + "/autostart")
            / "vorta.desktop"
        )
        qtbot.waitUntil(lambda: autostart_path.exists(), **pytest._wait_defaults)

        with open(autostart_path) as desktop_file:
            desktop_file_text = desktop_file.read()

        assert desktop_file_text.startswith("[Desktop Entry]")

    click_autostart()
    if sys.platform == 'linux':
        assert not os.path.exists(autostart_path)
