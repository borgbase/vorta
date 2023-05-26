import os
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
import vorta.store.models
from PyQt6 import QtCore
from PyQt6.QtWidgets import QCheckBox, QFormLayout


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


def test_enable_fixed_units(qapp, qtbot, mocker):
    """
    Mocks the 'enable fixed units' setting to ensure the correct function is called when displaying the archive size.
    """

    archive_tab = qapp.main_window.archiveTab

    # set mocks
    mock_setting = mocker.patch.object(vorta.views.archive_tab.SettingsModel, "get", return_value=Mock(value=True))
    mock_fixed = mocker.patch.object(vorta.views.archive_tab, "pretty_bytes_fixed_units")
    mock_dynamic = mocker.patch.object(vorta.views.archive_tab, "pretty_bytes_dynamic_units")

    # with setting enabled, fixed units should be used and not dynamic units
    archive_tab.populate_from_profile()
    mock_fixed.assert_called()
    mock_dynamic.assert_not_called()

    # reset mocks and disable setting
    mock_setting.return_value = Mock(value=False)
    mock_fixed.reset_mock()

    # with setting disabled, dynamic units should be used and not fixed units
    archive_tab.populate_from_profile()
    mock_dynamic.assert_called()
    mock_fixed.assert_not_called()


def test_emit_archive_refresh(qapp, qtbot, mocker):
    """
    When the 'enable fixed units' setting is changed, 'refresh_archive' in misc_tab should emit. This emit triggers
    main_window to call 'archive_tab.populate_from_profile' and refresh the archive tab with new archive size units.
    """

    setting = "Display all archive sizes in a consistent unit of measurement"

    # set up mocks
    mock_fixed = mocker.patch.object(vorta.views.archive_tab, "pretty_bytes_fixed_units")
    mock_dynamic = mocker.patch.object(vorta.views.archive_tab, "pretty_bytes_dynamic_units")

    # setting is disabled by default, so this click enables the fixed units setting
    # click toggle the setting, which triggers the emit that refreshes archive tab
    _click_toggle_setting(setting, qapp, qtbot)
    mock_fixed.assert_called()
    mock_dynamic.assert_not_called()

    # reset mocks
    mock_fixed.reset_mock()
    mock_dynamic.reset_mock()

    # click toggle disables the fixed units setting
    # emit should trigger a refresh of the archive tab to show dynamic units
    _click_toggle_setting(setting, qapp, qtbot)
    mock_dynamic.assert_called()
    mock_fixed.assert_not_called()


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
    """Toggle setting checkbox in the misc tab"""

    miscTab = qapp.main_window.miscTab

    for x in range(miscTab.checkboxLayout.count()):
        item = miscTab.checkboxLayout.itemAt(x, QFormLayout.ItemRole.FieldRole)
        if item is not None:
            checkbox = item.itemAt(0).widget()
            if checkbox.text() == setting and isinstance(checkbox, QCheckBox):
                # Have to use pos to click checkbox correctly
                # https://stackoverflow.com/questions/19418125/pysides-qtest-not-checking-box/24070484#24070484
                qtbot.mouseClick(
                    checkbox, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(2, int(checkbox.height() / 2))
                )
                break
