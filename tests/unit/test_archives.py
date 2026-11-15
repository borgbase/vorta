from collections import namedtuple
from threading import Event

import psutil
import pytest
from PyQt6 import QtCore
from PyQt6.QtWidgets import QMenu
from test_constants import TEST_TEMP_DIR

import vorta.borg
import vorta.utils
import vorta.views.archive_tab
from vorta.store.models import ArchiveModel, BackupProfileModel
from vorta.views.partials.archive_table_model import ArchiveTableModel


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
        tab.archive_maintenance.save_prune_setting(None)
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


def test_repo_list_prepare_error_is_translated(mocker, archive_env):
    _, tab = archive_env
    params = {'ok': False, 'message': 'Select a backup repository first.'}
    mocker.patch('vorta.views.archive_tab.BorgListRepoJob.prepare', return_value=params)
    translate = mocker.patch('vorta.views.archive_tab.translate', return_value='Translated prepare error')

    tab.refresh_archive_list()

    translate.assert_called_once_with('messages', params['message'])
    assert tab.mountErrors.text() == 'Translated prepare error'
    assert params['message'] == 'Select a backup repository first.'


@pytest.mark.parametrize('stdout_content', ['', 'not json', '{"foo": 1}', '{"archives": null}'])
def test_repo_list_invalid_output_keeps_archives(qapp, qtbot, mocker, archive_env, tmp_path, stdout_content):
    """Unreadable borg list output must not wipe the local archive list (#2412)."""
    main, tab = archive_env
    assert ArchiveModel.select().count() == 2

    (tmp_path / 'stdout').write_text(stdout_content)
    (tmp_path / 'stderr').write_text('')
    stdout, stderr = open(tmp_path / 'stdout'), open(tmp_path / 'stderr')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    tab._set_status('')
    try:
        tab.refresh_archive_list()
        qtbot.waitUntil(lambda: 'Local list kept' in tab.mountErrors.text(), **pytest._wait_defaults)
    finally:
        stdout.close()
        stderr.close()

    assert ArchiveModel.select().count() == 2
    assert tab.archiveTable.model().rowCount() == 2


def test_repo_list_empty_repo_removes_archives(qapp, qtbot, mocker, archive_env, tmp_path):
    main, tab = archive_env

    (tmp_path / 'stdout').write_text('{"archives": []}')
    (tmp_path / 'stderr').write_text('')
    stdout, stderr = open(tmp_path / 'stdout'), open(tmp_path / 'stderr')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    tab._set_status('')
    try:
        tab.refresh_archive_list()
        qtbot.waitUntil(lambda: 'Refreshed archives.' in tab.mountErrors.text(), **pytest._wait_defaults)
    finally:
        stdout.close()
        stderr.close()

    assert ArchiveModel.select().count() == 0


def test_repo_prune(qapp, qtbot, mock_borg_popen, archive_env):
    main, tab = archive_env

    mock_borg_popen(['prune', 'list'])

    qtbot.mouseClick(tab.bPrune, QtCore.Qt.MouseButton.LeftButton)

    qtbot.waitUntil(lambda: 'Refreshing archives done.' in main.progressText.text(), **pytest._wait_defaults)
    qtbot.waitUntil(lambda: ArchiveModel.select().count() == 6, **pytest._wait_defaults)


def test_repo_compact(qapp, qtbot, mocker, borg_json_output, archive_env):
    vorta.utils.borg_compat.version = '1.2.0'
    main, tab = archive_env
    tab.toggle_compact_button_visibility()

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
    tab.archive_delete.delete_action()
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
    col_name = ArchiveTableModel.COL_NAME

    # sort so the proxy's row order differs from the source order
    view.sortByColumn(col_name, QtCore.Qt.SortOrder.DescendingOrder)

    view.selectRow(0)
    displayed_name = view.model().index(0, col_name).data()
    selected = tab.selected_archives()

    assert len(selected) == 1
    assert selected[0].name == displayed_name


def test_rename_failure_reverts_optimistic_name(qapp, qtbot, archive_env):
    """A failed rename must not leave the optimistically-applied name in the table (D1)."""
    main, tab = archive_env
    model = tab.archive_model
    col = ArchiveTableModel.COL_NAME

    original = model.data(model.index(0, col))
    model.setData(model.index(0, col), 'optimistic-name')
    assert model.data(model.index(0, col)) == 'optimistic-name'

    tab.archive_rename.rename_result({'returncode': 2})

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


def test_refresh_archive_info_borg2(qapp, qtbot, mocker, monkeypatch, borg_json_output, archive_env):
    monkeypatch.setattr(vorta.utils.borg_compat, 'version', '2.0.0b25')
    main, tab = archive_env
    ArchiveModel.update(size=12345).where(ArchiveModel.snapshot_id == '99999').execute()
    tab.archiveTable.selectRow(0)
    stdout, stderr = borg_json_output('info_v2')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    with qtbot.waitSignal(tab.bRefreshArchive.clicked, timeout=5000):
        qtbot.mouseClick(tab.bRefreshArchive, QtCore.Qt.MouseButton.LeftButton)

    qtbot.waitUntil(lambda: tab.mountErrors.text() == 'Refreshed archives.', **pytest._wait_defaults)
    archive = ArchiveModel.get(snapshot_id='99999')
    assert archive.size == 12345
    assert archive.duration == 12.5


@pytest.mark.parametrize('failed_index', [0, 1])
def test_refresh_prepare_failure_keeps_buttons_enabled(qapp, mocker, archive_env, failed_index):
    _, tab = archive_env
    tab.archiveTable.selectAll()
    prepare = mocker.patch.object(vorta.views.archive_tab.BorgInfoArchiveJob, 'prepare')
    prepare.side_effect = [{'ok': True, 'cmd': ['borg', 'info']}] * failed_index + [
        {'ok': False, 'message': 'Repository password is missing.'}
    ]
    add_job = mocker.patch.object(qapp.jobs_manager, 'add_job')

    tab.refresh_archive_info()

    add_job.assert_not_called()
    assert tab.remaining_refresh_archives == 0
    assert tab.bCheck.isEnabled()
    assert tab.bRefreshArchive.isEnabled()
    assert tab.mountErrors.text() == 'Repository password is missing.'


def test_refresh_without_selection_keeps_buttons_enabled(mocker, archive_env):
    _, tab = archive_env
    tab.archiveTable.clearSelection()
    prepare = mocker.patch.object(vorta.views.archive_tab.BorgInfoArchiveJob, 'prepare')

    tab.refresh_archive_info()

    prepare.assert_not_called()
    assert tab.remaining_refresh_archives == 0
    assert tab.bCheck.isEnabled()


@pytest.mark.parametrize('start_new_refresh', [False, True])
def test_cancelled_refresh_ignores_late_results(qapp, mocker, archive_env, start_new_refresh):
    main, tab = archive_env
    tab.archiveTable.selectAll()
    add_job = mocker.patch.object(qapp.jobs_manager, 'add_job')
    tab.refresh_archive_info()
    old_job = add_job.call_args_list[0].args[0]
    assert tab.remaining_refresh_archives == 2

    qapp.backup_cancelled_event.emit()
    assert tab.remaining_refresh_archives == 0
    assert tab.bCheck.isEnabled()
    if start_new_refresh:
        tab.refresh_archive_info()
    expected = tab.remaining_refresh_archives
    old_job.result.emit({'returncode': 0, 'params': old_job.params})
    assert tab.remaining_refresh_archives == expected

    if start_new_refresh:
        for call in add_job.call_args_list[2:]:
            job = call.args[0]
            job.result.emit({'returncode': 0, 'params': job.params})
    assert tab.remaining_refresh_archives == 0
    main.backup_started_event()
    main.backup_finished_event()
    assert main.createStartBtn.isEnabled()
    assert tab.bCheck.isEnabled()


@pytest.mark.parametrize('version, supported', [('1.1.4', False), ('1.2.0', True)])
def test_compact_button_respects_version_and_busy_state(monkeypatch, archive_env, version, supported):
    _, tab = archive_env
    monkeypatch.setattr(vorta.utils.borg_compat, 'version', version)
    tab._toggle_all_buttons(True)
    assert tab.compactButton.isEnabled() == supported
    tab._toggle_all_buttons(False)
    tab.toggle_compact_button_visibility()
    assert not tab.compactButton.isEnabled()


def test_cancel_refresh_clears_queued_jobs(qapp, qtbot, mocker, mock_borg_popen, archive_env):
    main, tab = archive_env
    archive = ArchiveModel.select().first()
    ArchiveModel.create(name='third', snapshot_id='third', time=archive.time, repo=archive.repo)
    tab.populate_from_profile()
    tab.archiveTable.selectAll()
    release = Event()

    def run(job):
        job.started_event()
        if not release.wait(timeout=10):
            raise RuntimeError('Test did not release the running refresh')
        job.finished_event({'returncode': -2, 'params': job.params})

    run_job = mocker.patch.object(vorta.views.archive_tab.BorgInfoArchiveJob, 'run', autospec=True, side_effect=run)
    try:
        with qtbot.waitSignal(qapp.backup_started_event, **pytest._wait_defaults):
            tab.refresh_archive_info()
        assert tab.remaining_refresh_archives == 3
        qapp.backup_cancelled_event.emit()
    finally:
        release.set()

    qtbot.waitUntil(lambda: not qapp.jobs_manager.is_worker_running(), **pytest._wait_defaults)
    assert run_job.call_count == 1
    assert tab.remaining_refresh_archives == 0
    mock_borg_popen(['list'])
    tab.refresh_archive_list()
    qtbot.waitUntil(lambda: 'Refreshing archives done.' in main.progressText.text(), **pytest._wait_defaults)
    assert tab.remaining_refresh_archives == 0
    assert main.createStartBtn.isEnabled()
    assert tab.bCheck.isEnabled()


def test_inline_archive_rename(qapp, qtbot, mocker, mock_borg_popen, archive_env):
    """
    Tests the functionality of in-line renaming an archive.
    """
    main, tab = archive_env

    tab.archiveTable.selectRow(0)
    new_archive_name = 'idf89d8f9d8fd98'
    # A successful rename queues a `borg info` refresh of the renamed archive.
    mock_borg_popen(['rename', 'info'])

    # Trigger inline editing through the real entry point so is_editing / original name are set.
    index = tab.archiveTable.model().index(0, 4)
    tab.archiveTable.setCurrentIndex(index)
    tab.archive_rename.cell_double_clicked(index)

    # Wait for edit mode to activate
    qtbot.waitUntil(lambda: tab.archiveTable.viewport().focusWidget() is not None, **pytest._wait_defaults)

    editor = tab.archiveTable.viewport().focusWidget()
    editor.setText(new_archive_name)
    qtbot.keyClick(editor, QtCore.Qt.Key.Key_Return)

    # Successful rename case
    qtbot.waitUntil(lambda: tab.archiveTable.model().index(0, 4).data() == new_archive_name, **pytest._wait_defaults)
    assert tab.archiveTable.model().index(0, 4).data() == new_archive_name

    # The rename result queues a refresh of the selected archives, if any. Let it finish here,
    # so it does not run into the next test.
    qtbot.waitUntil(
        lambda: tab.remaining_refresh_archives == 0
        and tab.mountErrors.text() in ('Archive renamed.', 'Refreshed archives.')
        and not qapp.jobs_manager.is_worker_running(),
        **pytest._wait_defaults,
    )


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
