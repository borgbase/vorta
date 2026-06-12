from collections import namedtuple

import psutil
import pytest
from PyQt6 import QtCore
from PyQt6.QtWidgets import QMenu
from test_constants import TEST_TEMP_DIR

import vorta.borg
import vorta.utils
import vorta.views.archive_tab
from vorta.store.models import ArchiveModel, BackupProfileModel


class MockFileDialog:
    def open(self, func):
        func()

    def selectedFiles(self):
        return [TEST_TEMP_DIR]


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


def test_populate_does_not_overwrite_prune_keep_within(qapp, qtbot):
    """Loading a profile must not fire save_prune_setting and overwrite
    prune_keep_within with stale QLineEdit text (#2493)."""
    main = qapp.main_window
    tab = main.archiveTab
    profile = BackupProfileModel.get(id=1)
    profile.prune_keep_within = '10H'
    profile.prune_hour = 7
    profile.save()

    # Simulate stale UI state: a spinbox value differs from the DB (so the
    # setValue call inside populate_from_profile would otherwise fire
    # valueChanged -> save_prune_setting) and the prune_keep_within QLineEdit
    # holds stale text from another profile. Block signals while setting this
    # up so the pre-state itself doesn't overwrite the DB values just saved.
    tab.prune_hour.blockSignals(True)
    try:
        tab.prune_hour.setValue(1)
    finally:
        tab.prune_hour.blockSignals(False)
    tab.prune_keep_within.setText('')

    tab.populate_from_profile()

    profile = profile.refresh()
    assert profile.prune_keep_within == '10H'
    assert tab.prune_keep_within.text() == '10H'


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
        return [DiskPartitions('borgfs', TEST_TEMP_DIR)]

    monkeypatch.setattr(psutil, "disk_partitions", psutil_disk_partitions)
    main, tab = archive_env
    tab.archiveTable.selectRow(0)

    stdout, stderr = borg_json_output('prune')  # TODO: fully mock mount command?
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    monkeypatch.setattr("vorta.views.archive.archive_mount.choose_file_dialog", choose_file_dialog)

    tab.archive_mount.bmountarchive_clicked()
    qtbot.waitUntil(lambda: tab.mountErrors.text().startswith('Mounted'), **pytest._wait_defaults)

    tab.archive_mount.bmountarchive_clicked()
    qtbot.waitUntil(lambda: tab.mountErrors.text().startswith('Un-mounted successfully.'), **pytest._wait_defaults)

    tab.archive_mount.bmountrepo_clicked()
    qtbot.waitUntil(lambda: tab.mountErrors.text().startswith('Mounted'), **pytest._wait_defaults)

    tab.archive_mount.bmountrepo_clicked()
    qtbot.waitUntil(lambda: tab.mountErrors.text().startswith('Un-mounted successfully.'), **pytest._wait_defaults)


def test_archive_extract(qapp, qtbot, mocker, borg_json_output, archive_env):
    main, tab = archive_env
    tab.archiveTable.selectRow(0)
    stdout, stderr = borg_json_output('list_archive')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)
    tab.archive_extract.extract_action()

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
    assert tab.archiveTable.model().rowCount() == 1


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


def test_selection_maps_through_sort_proxy(qapp, qtbot, archive_env):
    """R1: selected_archives() returns the archive shown at the selected row, even after sorting."""
    main, tab = archive_env
    view = tab.archiveTable
    col_name = vorta.views.archive_tab.ArchiveTableModel.COL_NAME

    # Sort by Name descending so the proxy's row order differs from the source order.
    view.sortByColumn(col_name, QtCore.Qt.SortOrder.DescendingOrder)

    view.selectRow(0)
    displayed_name = view.model().index(0, col_name).data()
    selected = tab.selected_archives()

    assert len(selected) == 1
    # If the helper used the proxy row as a source row, this would resolve to the wrong archive.
    assert selected[0].name == displayed_name


def test_rename_failure_reverts_optimistic_name(qapp, qtbot, archive_env):
    """A failed rename must not leave the optimistically-applied name in the table (D1)."""
    main, tab = archive_env
    model = tab.archive_model
    col = vorta.views.archive_tab.ArchiveTableModel.COL_NAME

    original = model.data(model.index(0, col))
    # Simulate the editor having committed a new name optimistically.
    model.setData(model.index(0, col), 'optimistic-name')
    assert model.data(model.index(0, col)) == 'optimistic-name'

    # Borg reports the rename failed -> the table must refresh back to the DB's original name.
    tab.rename_result({'returncode': 2})

    assert model.data(model.index(0, col)) == original


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
    Tests the functionality of in-line renaming an archive.
    """
    main, tab = archive_env

    tab.archiveTable.selectRow(0)
    new_archive_name = 'idf89d8f9d8fd98'
    stdout, stderr = borg_json_output('rename')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    # Trigger inline editing through the real entry point so is_editing / original name are set.
    index = tab.archiveTable.model().index(0, 4)
    tab.archiveTable.setCurrentIndex(index)
    tab.cell_double_clicked(index)

    # Wait for edit mode to activate
    qtbot.waitUntil(lambda: tab.archiveTable.viewport().focusWidget() is not None, **pytest._wait_defaults)

    editor = tab.archiveTable.viewport().focusWidget()
    editor.setText(new_archive_name)
    qtbot.keyClick(editor, QtCore.Qt.Key.Key_Return)

    # Successful rename case
    qtbot.waitUntil(lambda: tab.archiveTable.model().index(0, 4).data() == new_archive_name, **pytest._wait_defaults)
    assert tab.archiveTable.model().index(0, 4).data() == new_archive_name


def test_archiveitem_contextmenu(qapp, qtbot, archive_env):
    main, tab = archive_env

    pos = tab.archiveTable.visualRect(tab.archiveTable.model().index(0, 0)).center()
    tab.archiveTable.customContextMenuRequested.emit(pos)
    qtbot.waitUntil(lambda: tab.archiveTable.findChild(QMenu) is not None, **pytest._wait_defaults)

    context_menu = tab.archiveTable.findChild(QMenu)

    assert context_menu is not None
    expected_actions = ['Copy', 'Recalculate', 'Mount…', 'Extract…', 'Rename…', 'Delete', 'Diff']
    for action in expected_actions:
        assert any(menu_actions.text() == action for menu_actions in context_menu.actions())
