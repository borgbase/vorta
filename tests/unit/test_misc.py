import os
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
import vorta.store.models
from PyQt6 import QtCore
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QCheckBox, QFormLayout, QMessageBox
from vorta.store.models import SettingsModel


def test_toggle_all_settings(qapp, qtbot):
    """Toggle each setting twice as a basic sanity test to ensure app does crash."""
    groups = (
        SettingsModel.select(SettingsModel.group)
        .distinct(True)
        .where(SettingsModel.group != '')
        .order_by(SettingsModel.group.asc())
    )

    settings = [
        setting
        for group in groups
        for setting in SettingsModel.select().where(
            SettingsModel.type == 'checkbox', SettingsModel.group == group.group
        )
    ]

    for setting in settings:
        for _ in range(2):
            _click_toggle_setting(setting.label, qapp, qtbot)


@pytest.mark.skipif(sys.platform != "linux", reason="testing autostart path for Linux only")
def test_autostart_linux(qapp, qtbot):
    """Checks that autostart path is added correctly on Linux when setting is enabled."""
    setting = "Automatically start Vorta at login"

    # ensure file is present when autostart is enabled
    _click_toggle_setting(setting, qapp, qtbot)
    autostart_path = (
        Path(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~") + '/.config') + "/autostart") / "vorta.desktop"
    )
    qtbot.waitUntil(lambda: autostart_path.exists(), **pytest._wait_defaults)
    with open(autostart_path) as desktop_file:
        desktop_file_text = desktop_file.read()
    assert desktop_file_text.startswith("[Desktop Entry]")

    # ensure file is removed when autostart is disabled
    _click_toggle_setting(setting, qapp, qtbot)
    if sys.platform == 'linux':
        assert not os.path.exists(autostart_path)


def test_enable_background_question(qapp, monkeypatch, mocker):
    """Tests that 'enable background question' correctly prompts user."""
    main = qapp.main_window
    close_event = Mock(value=QCloseEvent())

    # disable system trey and enable setting to test
    monkeypatch.setattr("vorta.views.main_window.is_system_tray_available", lambda: False)
    mocker.patch.object(vorta.store.models.SettingsModel, "get", return_value=Mock(value=True))
    mocker.patch.object(QMessageBox, "exec")  # prevent QMessageBox from stopping test

    # Create a mock for QMessageBox and its setText method
    mock_msgbox = mocker.Mock(spec=QMessageBox)
    mocker.patch("vorta.views.main_window.QMessageBox", return_value=mock_msgbox)

    main.closeEvent(close_event)

    mock_msgbox.setText.assert_called_once_with("Should Vorta continue to run in the background?")
    close_event.accept.assert_called_once()


def test_enable_fixed_units(qapp, qtbot, mocker):
    """Tests the 'enable fixed units' setting to ensure the archive tab sizes are displayed correctly."""
    tab = qapp.main_window.archiveTab
    setting = "Use the same unit of measurement for archive sizes"

    # set mocks
    mock_setting = mocker.patch.object(vorta.views.archive_tab.SettingsModel, "get", return_value=Mock(value=True))
    mock_pretty_bytes = mocker.patch.object(vorta.views.archive_tab, "pretty_bytes")

    # with setting enabled, fixed units should be determined and passed to pretty_bytes as an 'int'
    tab.populate_from_profile()
    mock_pretty_bytes.assert_called()
    kwargs_list = mock_pretty_bytes.call_args_list[0].kwargs
    assert 'fixed_unit' in kwargs_list
    assert isinstance(kwargs_list['fixed_unit'], int)

    # disable setting and reset mock
    mock_setting.return_value = Mock(value=False)
    mock_pretty_bytes.reset_mock()

    # with setting disabled, pretty_bytes should be called with fixed units set to 'None'
    tab.populate_from_profile()
    mock_pretty_bytes.assert_called()
    kwargs_list = mock_pretty_bytes.call_args_list[0].kwargs
    assert 'fixed_unit' in kwargs_list
    assert kwargs_list['fixed_unit'] is None

    # use the qt bot to click the setting and see that the refresh_archive emit works as intended.
    with qtbot.waitSignal(qapp.main_window.miscTab.refresh_archive, **pytest._wait_defaults):
        _click_toggle_setting(setting, qapp, qtbot)


@pytest.mark.skipif(sys.platform != 'darwin', reason="Full Disk Access check only on Darwin")
def test_check_full_disk_access(qapp, mocker):
    """Tests if the full disk access warning is properly silenced with the setting enabled"""

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
                pos = QtCore.QPoint(2, int(checkbox.height() / 2))
                qtbot.mouseClick(checkbox, QtCore.Qt.MouseButton.LeftButton, pos=pos)
                break
