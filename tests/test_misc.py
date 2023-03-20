import os
import sys
from pathlib import Path
from unittest.mock import Mock
import pytest
from PyQt5 import QtCore
from PyQt5.QtWidgets import QCheckBox, QFormLayout
import vorta.store.models


def test_autostart(qapp, qtbot):
    """Check if file exists only on Linux, otherwise just check it doesn't crash"""

    setting = "Automatically start Vorta at login"

    _click_toggle_setting(setting, qapp, qtbot)

    if sys.platform == 'linux':
        autostart_path = (
            Path(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~") + '/.config') + "/autostart")
            / "vorta.desktop"
        )
        qtbot.waitUntil(lambda: autostart_path.exists(), **pytest._wait_defaults)

        with open(autostart_path) as desktop_file:
            desktop_file_text = desktop_file.read()

        assert desktop_file_text.startswith("[Desktop Entry]")

    _click_toggle_setting(setting, qapp, qtbot)

    if sys.platform == 'linux':
        assert not os.path.exists(autostart_path)


def test_full_disk_access_check_disabled(qapp, mocker):
    """Mock disables the setting 'Check for Full Disk Access on startup' and ensures functionality"""

    # Set mocks
    mocker.patch.object(vorta.store.models.SettingsModel, "get", return_value=Mock(value=False))
    mocker.patch('pathlib.Path.exists', return_value=True)
    mocker.patch('os.access', return_value=False)
    mock_qmessagebox = mocker.patch('vorta.application.QMessageBox')

    qapp.check_darwin_permissions()

    # See that no pop-up occurs
    mock_qmessagebox.assert_not_called()


def test_full_disk_access_check_enabled(qapp, mocker):
    """Mock enables the setting 'Check for Full Disk Access on startup' and ensures functionality"""

    # Set mocks
    mocker.patch.object(vorta.store.models.SettingsModel, "get", return_value=Mock(value=True))
    mocker.patch('pathlib.Path.exists', return_value=True)
    mocker.patch('os.access', return_value=False)
    mock_qmessagebox = mocker.patch('vorta.application.QMessageBox')

    qapp.check_darwin_permissions()

    # see that pop-up occurs
    mock_qmessagebox.assert_called()


@pytest.mark.skipif(sys.platform != 'darwin', reason="Full Disk Access check only on Darwin")
def test_toggle_full_disk_access_setting(qapp, qtbot, mocker):
    """On darwin, checks that setting doesn't crash program when toggled on/off"""

    setting = "Check for Full Disk Access on startup"
    _click_toggle_setting(setting, qapp, qtbot)
    _click_toggle_setting(setting, qapp, qtbot)


def _click_toggle_setting(setting, qapp, qtbot):
    """Uses qtbot to click toggle setting in the misc tab"""

    main = qapp.main_window
    main.tabWidget.setCurrentIndex(4)
    tab = main.miscTab

    for x in range(0, tab.checkboxLayout.count()):
        item = tab.checkboxLayout.itemAt(x, QFormLayout.ItemRole.FieldRole)
        if not item:
            continue
        checkbox = item.itemAt(0).widget()
        checkbox.__class__ = QCheckBox

        if checkbox.text() == setting:
            # Have to use pos to click checkbox correctly
            # https://stackoverflow.com/questions/19418125/pysides-qtest-not-checking-box/24070484#24070484
            qtbot.mouseClick(checkbox, QtCore.Qt.LeftButton, pos=QtCore.QPoint(2, int(checkbox.height() / 2)))
            break
