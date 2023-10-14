from collections import namedtuple

import psutil
import pytest
import vorta.borg
import vorta.utils
import vorta.views.archive_tab
from PyQt6 import QtCore
from PyQt6.QtWidgets import QMenu
from vorta.store.models import ArchiveModel, BackupProfileModel


class MockFileDialog:
    def open(self, func):
        func()

    def selectedFiles(self):
        return ['/tmp']


def test_prune_intervals(qapp, qtbot):
    prune_intervals = ['hour', 'day', 'week', 'month', 'year']
    main = qapp.main_window
    tab = main.archiveTab
    profile = BackupProfileModel.get(id=1)

    for i in prune_intervals:
        getattr(tab, f'prune_{i}').setValue(9)
        tab.save_prune_setting(None)
        profile = profile.refresh()
        assert getattr(profile, f'prune_{i}') == 9


def test_repo_list(qapp, qtbot, mocker, borg_json_output, archive_env):
    main, tab = archive_env

    stdout, stderr = borg_json_output('list')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    tab.refresh_archive_list()
    qtbot.waitUntil(lambda: not tab.bCheck.isEnabled(), **pytest._wait_defaults)
    assert not tab.bCheck.isEnabled()

    qtbot.waitUntil(lambda: 'Refreshing archives done.' in main.progressText.text(), **pytest._wait_defaults)
    assert ArchiveModel.select().count() == 6
    assert 'Refreshing archives done.' in main.progressText.text()
    assert tab.bCheck.isEnabled()


def test_repo_prune(qapp, qtbot, mocker, borg_json_output, archive_env):
    main, tab = archive_env

    stdout, stderr = borg_json_output('prune')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    qtbot.mouseClick(tab.bPrune, QtCore.Qt.MouseButton.LeftButton)

    qtbot.waitUntil(lambda: 'Refreshing archives done.' in main.progressText.text(), **pytest._wait_defaults)


def test_repo_compact(qapp, qtbot, mocker, borg_json_output, archive_env):
    vorta.utils.borg_compat.version = '1.2.0'
    main, tab = archive_env

    stdout, stderr = borg_json_output('compact')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    qtbot.mouseClick(tab.compactButton, QtCore.Qt.MouseButton.LeftButton)

    qtbot.waitUntil(
        lambda: 'compaction freed about 56.00 kB repository space' in main.logText.text(), **pytest._wait_defaults
    )
    vorta.utils.borg_compat.version = '1.1.0'


def test_check(qapp, mocker, borg_json_output, qtbot, archive_env):
    main, tab = archive_env

    stdout, stderr = borg_json_output('check')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    qtbot.mouseClick(tab.bCheck, QtCore.Qt.MouseButton.LeftButton)
    success_text = 'INFO: Archive consistency check complete'
    qtbot.waitUntil(lambda: success_text in main.logText.text(), **pytest._wait_defaults)


def test_mount(qapp, qtbot, mocker, borg_json_output, monkeypatch, choose_file_dialog, archive_env):
    def psutil_disk_partitions(**kwargs):
        DiskPartitions = namedtuple('DiskPartitions', ['device', 'mountpoint'])
        return [DiskPartitions('borgfs', '/tmp')]

    monkeypatch.setattr(psutil, "disk_partitions", psutil_disk_partitions)
    main, tab = archive_env
    tab.archiveTable.selectRow(0)

    stdout, stderr = borg_json_output('prune')  # TODO: fully mock mount command?
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    monkeypatch.setattr(vorta.views.archive_tab, "choose_file_dialog", choose_file_dialog)

    tab.bmountarchive_clicked()
    qtbot.waitUntil(lambda: tab.mountErrors.text().startswith('Mounted'), **pytest._wait_defaults)

    tab.bmountarchive_clicked()
    qtbot.waitUntil(lambda: tab.mountErrors.text().startswith('Un-mounted successfully.'), **pytest._wait_defaults)

    tab.bmountrepo_clicked()
    qtbot.waitUntil(lambda: tab.mountErrors.text().startswith('Mounted'), **pytest._wait_defaults)

    tab.bmountrepo_clicked()
    qtbot.waitUntil(lambda: tab.mountErrors.text().startswith('Un-mounted successfully.'), **pytest._wait_defaults)


def test_archive_extract(qapp, qtbot, mocker, borg_json_output, archive_env):
    main, tab = archive_env
    tab.archiveTable.selectRow(0)
    stdout, stderr = borg_json_output('list_archive')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)
    tab.extract_action()

    qtbot.waitUntil(lambda: hasattr(tab, '_window'), **pytest._wait_defaults)

    model = tab._window.model
    assert model.root.children[0].subpath == 'home'
    assert 'test-archive, 2000' in tab._window.archiveNameLabel.text()


def test_archive_delete(qapp, qtbot, mocker, borg_json_output, archive_env):
    main, tab = archive_env

    tab.archiveTable.selectRow(0)
    stdout, stderr = borg_json_output('delete')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)
    mocker.patch.object(vorta.views.archive_tab.ArchiveTab, 'confirm_dialog', lambda x, y, z: True)
    tab.delete_action()
    qtbot.waitUntil(lambda: 'Archive deleted.' in main.progressText.text(), **pytest._wait_defaults)
    assert ArchiveModel.select().count() == 1
    assert tab.archiveTable.rowCount() == 1


def test_archive_copy(qapp, qtbot, monkeypatch, mocker, archive_env):
    main, tab = archive_env

    # mock the clipboard to ensure no changes are made to it during testing
    mocker.patch.object(qapp.clipboard(), "setMimeData")
    clipboard_spy = mocker.spy(qapp.clipboard(), "setMimeData")

    # test 'archive_copy()' by passing it an index to copy
    index = tab.archiveTable.model().index(0, 0)
    tab.archive_copy(index)
    assert clipboard_spy.call_count == 1
    actual_data = clipboard_spy.call_args[0][0]  # retrieves the QMimeData() object used in method call
    assert actual_data.text() == "test-archive"

    # test 'archive_copy()' by selecting a row to copy
    tab.archiveTable.selectRow(1)
    tab.archive_copy()
    assert clipboard_spy.call_count == 2
    actual_data = clipboard_spy.call_args[0][0]  # retrieves the QMimeData() object used in method call
    assert actual_data.text() == "test-archive1"


def test_refresh_archive_info(qapp, qtbot, mocker, borg_json_output, archive_env):
    main, tab = archive_env
    tab.archiveTable.selectRow(0)
    stdout, stderr = borg_json_output('info')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    with qtbot.waitSignal(tab.bRefreshArchive.clicked, timeout=5000):
        qtbot.mouseClick(tab.bRefreshArchive, QtCore.Qt.MouseButton.LeftButton)

    qtbot.waitUntil(lambda: tab.mountErrors.text() == 'Refreshed archives.', **pytest._wait_defaults)


def test_inline_archive_rename(qapp, qtbot, mocker, borg_json_output, archive_env):
    """
    Tests the functionality of in-line renaming an archive by double-clicking its name.
    """
    main, tab = archive_env

    tab.archiveTable.selectRow(0)
    new_archive_name = 'idf89d8f9d8fd98'
    stdout, stderr = borg_json_output('rename')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    pos = tab.archiveTable.visualRect(tab.archiveTable.model().index(0, 4)).center()
    qtbot.mouseClick(tab.archiveTable.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=pos)
    assert tab.bRename.isEnabled()
    qtbot.mouseDClick(tab.archiveTable.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=pos)
    tab.archiveTable.viewport().focusWidget().setText("")
    qtbot.keyClicks(tab.archiveTable.viewport().focusWidget(), new_archive_name)
    qtbot.keyClick(tab.archiveTable.viewport().focusWidget(), QtCore.Qt.Key.Key_Return)

    # Successful rename case
    qtbot.waitUntil(lambda: tab.archiveTable.model().index(0, 4).data() == new_archive_name, **pytest._wait_defaults)
    assert tab.archiveTable.model().index(0, 4).data() == new_archive_name


def test_archiveitem_contextmenu(qapp, qtbot, archive_env):
    main, tab = archive_env

    pos = tab.archiveTable.visualRect(tab.archiveTable.model().index(0, 0)).center()
    tab.archiveTable.customContextMenuRequested.emit(pos)
    qtbot.waitUntil(lambda: tab.archiveTable.findChild(QMenu) is not None, timeout=2000)

    context_menu = tab.archiveTable.findChild(QMenu)

    assert context_menu is not None
    expected_actions = ['Copy', 'Recalculate', 'Mount…', 'Extract…', 'Rename…', 'Delete', 'Diff']
    for action in expected_actions:
        assert any(menu_actions.text() == action for menu_actions in context_menu.actions())
