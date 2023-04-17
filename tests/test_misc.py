import os
import sys
from pathlib import Path
from unittest.mock import Mock
import pytest
from PyQt6 import QtCore
from PyQt6.QtWidgets import QCheckBox, QFormLayout
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


@pytest.mark.skipif(sys.platform != 'darwin', reason="Full Disk Access check only on Darwin")
def test_check_full_disk_access(qapp, qtbot, mocker):
    """Enables/disables 'Check for Full Disk Access on startup' setting and ensures functionality"""

    setting = "Check for Full Disk Access on startup"

    # Set mocks for setting enabled
    mocker.patch.object(vorta.store.models.SettingsModel, "get", return_value=Mock(value=True))
    mocker.patch('pathlib.Path.exists', return_value=True)
    mocker.patch('os.access', return_value=False)
    mock_qmessagebox = mocker.patch('vorta.application.QMessageBox')

    # See that pop-up occurs
    qapp.check_darwin_permissions()
    mock_qmessagebox.assert_called()

    # Reset mocks for setting disabled
    mock_qmessagebox.reset_mock()
    mocker.patch.object(vorta.store.models.SettingsModel, "get", return_value=Mock(value=False))

    # See that pop-up does not occur
    qapp.check_darwin_permissions()
    mock_qmessagebox.assert_not_called()

    # Checks that setting doesn't crash program when click toggled on then off"""
    _click_toggle_setting(setting, qapp, qtbot)
    _click_toggle_setting(setting, qapp, qtbot)


def _click_toggle_setting(setting, qapp, qtbot):
    """Click toggle setting in the misc tab"""

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
            qtbot.mouseClick(
                checkbox, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(2, int(checkbox.height() / 2))
            )
            break
