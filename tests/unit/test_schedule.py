from datetime import datetime as dt
from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from PyQt6 import QtCore
from PyQt6.QtWidgets import QDialogButtonBox, QFileDialog, QMessageBox, QWidget

import vorta.scheduler
import vorta.scheduler.execution
import vorta.scheduler.scheduling
import vorta.scheduler.state
from tests.unit.conftest import wait_for_workers
from vorta.application import VortaApp
from vorta.profile_export import ProfileExport
from vorta.store.models import BackupProfileModel, EventLogModel, JobModel, RepoModel
from vorta.views.partials.jobs_table_model import JobsTableModel
from vorta.views.schedule_tab import ScheduleTab

PROFILE_NAME = 'Default'


@pytest.fixture
def clockmock(monkeypatch):
    datetime_mock = MagicMock(wraps=dt)
    for module in (vorta.scheduler, vorta.scheduler.execution, vorta.scheduler.scheduling, vorta.scheduler.state):
        monkeypatch.setattr(module, "dt", datetime_mock)

    return datetime_mock


def test_schedule_tab(qapp: VortaApp, qtbot, clockmock):
    main = qapp.main_window
    tab = main.scheduleTab.schedulePage

    # setup
    time_now = dt(2020, 5, 6, 4, 30)
    clockmock.now.return_value = time_now

    # Work around
    # because already 'deleted' scheduletabs are still connected to the signal
    qapp.scheduler.schedule_changed.connect(tab.draw_next_scheduled_backup)

    # Test
    qtbot.mouseClick(tab.scheduleOffRadio, QtCore.Qt.MouseButton.LeftButton)
    assert tab.nextBackupDateTimeLabel.text() == 'None scheduled'

    tab.scheduleIntervalCount.setValue(5)
    qtbot.mouseClick(tab.scheduleIntervalRadio, QtCore.Qt.MouseButton.LeftButton)
    assert "None" not in tab.nextBackupDateTimeLabel.text()

    tab.scheduleFixedTime.setTime(QtCore.QTime(23, 59))

    # Clicking currently broken for this button on github.com only
    # qtbot.mouseClick(tab.scheduleFixedRadio, QtCore.Qt.MouseButton.LeftButton)

    # Workaround for github
    tab.scheduleFixedRadio.setChecked(True)
    tab.scheduleFixedRadio.clicked.emit()

    assert tab.nextBackupDateTimeLabel.text() == 'Run a manual backup first'

    next_backup = time_now.replace(hour=23, minute=59)
    last_time = time_now - timedelta(days=2)

    # setup model
    profile = BackupProfileModel.get(name=PROFILE_NAME)
    profile.schedule_make_up_missed = False
    profile.save()
    event = EventLogModel(
        subcommand='create',
        profile=profile.id,
        returncode=0,
        category='scheduled',
        start_time=last_time,
        end_time=last_time,
    )
    event.save()

    qapp.scheduler.set_timer_for_profile(profile.id)
    tab.draw_next_scheduled_backup()

    assert tab.nextBackupDateTimeLabel.text() not in [
        "Run a manual backup first",
        "None scheduled",
    ]
    assert qapp.scheduler.next_job_for_profile(profile.id).time == next_backup

    qapp.scheduler.remove_job(profile.id)


def test_schedule_tab_forwards_profile_provider_to_child_pages(qapp: VortaApp, qtbot):
    profile = BackupProfileModel.get(name=PROFILE_NAME)
    host = QWidget()
    qtbot.addWidget(host)
    tab = ScheduleTab(host, profile_provider=lambda: BackupProfileModel.get(id=profile.id))

    assert tab.schedulePage.profile().id == profile.id
    assert tab.shellCommandsPage.profile().id == profile.id
    assert tab.networksPage.profile().id == profile.id
    assert tab.logPage.profile().id == profile.id
    assert tab.jobsPage.profile().id == profile.id


def test_jobs_page_merges_pending_runs_with_stored_records(qapp: VortaApp, qtbot, clockmock, mocker):
    """The jobs page shows both halves, and a skip that pauses the profile must not empty either one."""
    page = qapp.main_window.scheduleTab.jobsPage

    time_now = dt(2020, 5, 6, 4, 30)
    clockmock.now.return_value = time_now

    profile = BackupProfileModel.get(name=PROFILE_NAME)
    profile.schedule_make_up_missed = False
    profile.schedule_mode = 'interval'
    profile.schedule_interval_unit = 'hours'
    profile.schedule_interval_count = 3
    profile.save()

    EventLogModel.create(
        subcommand='create',
        profile=profile.id,
        returncode=0,
        category='scheduled',
        start_time=time_now,
        end_time=time_now,
    )

    # Arming a timer emits `schedule_changed`, which is what the page listens to for pending runs.
    qapp.scheduler.set_timer_for_profile(profile.id)

    model = page.jobsTable.model()

    def statuses():
        return {model.data(model.index(row, JobsTableModel.COL_STATUS)) for row in range(model.rowCount())}

    # The page outlives earlier tests, so take its record count as the baseline rather than assuming zero.
    page.reload_records()
    rows_before = model.rowCount()
    assert JobModel.Status.SCHEDULED.value in statuses()
    assert JobModel.Status.PAUSED.value not in statuses()

    # A busy repo records a skip and pauses the profile, with no Borg job to announce either.
    mocker.patch.object(qapp.jobs_manager, 'is_worker_running', return_value=True)
    qapp.scheduler.create_backup(profile.id)

    # One row more: the skip arrives on its own signal, and the paused run keeps its row instead of vanishing.
    qtbot.waitUntil(lambda: model.rowCount() == rows_before + 1)
    assert JobModel.Status.PAUSED.value in statuses()
    assert JobModel.Status.SKIPPED.value in statuses()

    qapp.scheduler.unpause(profile.id)


def test_jobs_page_filter_combos_follow_the_rows(qapp: VortaApp):
    """Profile choices are rebuilt from the rows, and neither a reload nor a vanished value drops the selection."""
    page = qapp.main_window.scheduleTab.jobsPage
    page.reload_records()
    model = page.jobsTable.model()

    record = JobModel.create(
        profile=1,
        profile_name='FilterTestProfile',
        repo_url='filter-test-repo',
        job_type=JobModel.Type.BACKUP.value,
        status=JobModel.Status.FAILED.value,
        trigger=JobModel.Trigger.SCHEDULED.value,
        created_at=dt(2020, 5, 6, 4, 30),
    )
    page.reload_records()
    rows_unfiltered = model.rowCount()

    page.profileFilter.setCurrentIndex(page.profileFilter.findData('FilterTestProfile'))
    assert model.rowCount() == 1

    # A reload rebuilds the combo, and the view the user set up has to survive it.
    page.reload_records()
    assert page.profileFilter.currentData() == 'FilterTestProfile'
    assert model.rowCount() == 1

    # A value can leave the rows on an unrelated event, so it stays on offer rather than resetting the filter.
    record.delete_instance()
    page.reload_records()

    assert page.profileFilter.currentData() == 'FilterTestProfile'
    assert page.profileFilter.findData('FilterTestProfile') != -1
    assert model.rowCount() == 0

    page.profileFilter.setCurrentIndex(0)
    assert model.rowCount() == rows_unfiltered - 1


def _schedule_row(profile_id):
    p = BackupProfileModel.get(id=profile_id)
    return (
        p.schedule_mode,
        p.schedule_interval_unit,
        p.schedule_interval_count,
        p.schedule_fixed_hour,
        p.schedule_fixed_minute,
    )


def _select_profile(main, profile):
    for row in range(main.profileSelector.count()):
        if main.profileSelector.item(row).data(QtCore.Qt.ItemDataRole.UserRole) == profile.id:
            main.profileSelector.setCurrentRow(row)
            return
    raise AssertionError(f'{profile.name} not in profile selector')


@pytest.fixture
def restore_default_profile(qapp):
    yield
    # This window keeps receiving profile_changed_event until its deleteLater runs, and Profile B
    # does not exist in the next test's DB.
    qapp.main_window.current_profile = BackupProfileModel.get(name=PROFILE_NAME)


def _switch_from_a_to_b(qapp, mocker, tmp_path, a_schedule, b_schedule, b_last_run):
    create_backup = mocker.patch.object(qapp.scheduler, 'create_backup')
    # A still-running startup `borg --version` job would overwrite B's event-log row when it ends,
    # leaving no catch-up due and making the create_backup assertion vacuous.
    wait_for_workers(qapp.jobs_manager)
    main = qapp.main_window
    repo_b = RepoModel.create(url=str(tmp_path / 'repo-b'), encryption='none')  # local, so catch-up ignores network
    profile_a = BackupProfileModel.create(name='Profile A', **a_schedule)
    profile_b = BackupProfileModel.create(name='Profile B', repo=repo_b.id, schedule_make_up_missed=True, **b_schedule)
    EventLogModel.create(
        subcommand='create',
        category='scheduled',
        profile=profile_b.id,
        returncode=0,
        start_time=b_last_run,
        end_time=b_last_run,
    )
    main.populate_profile_selector()
    b_before = _schedule_row(profile_b.id)

    armed_b_rows = []
    set_timer = qapp.scheduler.set_timer_for_profile

    def record(profile_id):
        if profile_id == profile_b.id:
            armed_b_rows.append(_schedule_row(profile_id))
        set_timer(profile_id)

    mocker.patch.object(qapp.scheduler, 'set_timer_for_profile', side_effect=record)
    saves = mocker.spy(BackupProfileModel, 'save')

    def b_saves():
        return sum(1 for c in saves.call_args_list if c.args[0].id == profile_b.id)

    _select_profile(main, profile_a)
    _select_profile(main, profile_b)

    assert main.current_profile.id == profile_b.id
    assert armed_b_rows == []
    assert b_saves() == 0
    assert _schedule_row(profile_b.id) == b_before
    create_backup.assert_not_called()

    page = main.scheduleTab.schedulePage
    assert page.scheduleIntervalUnit.currentData() == b_before[1]
    assert page.scheduleIntervalCount.value() == b_before[2]
    assert page.scheduleFixedTime.time() == QtCore.QTime(*b_before[3:])

    # Positive control: a real edit after the switch still saves B and re-arms it from B's own values.
    edited_count = b_before[2] + 1
    page.scheduleIntervalCount.setValue(edited_count)
    expected = b_before[:2] + (edited_count,) + b_before[3:]
    assert armed_b_rows == [expected]
    assert b_saves() == 1
    assert _schedule_row(profile_b.id) == expected
    return page


def test_profile_switch_interval_does_not_save_or_catch_up(qapp, mocker, clockmock, tmp_path, restore_default_profile):
    now = dt(2020, 5, 6, 12, 0)
    clockmock.now.return_value = now
    page = _switch_from_a_to_b(
        qapp,
        mocker,
        tmp_path,
        a_schedule=dict(schedule_mode='interval', schedule_interval_unit='days', schedule_interval_count=1),
        b_schedule=dict(schedule_mode='interval', schedule_interval_unit='hours', schedule_interval_count=12),
        b_last_run=now - timedelta(hours=3),
    )
    assert page.scheduleIntervalRadio.isChecked()
    assert page.framePeriodic.isEnabled() and not page.frameDaily.isEnabled()


def test_profile_switch_fixed_does_not_save_or_catch_up(qapp, mocker, clockmock, tmp_path, restore_default_profile):
    clockmock.now.return_value = dt(2020, 5, 6, 19, 4)
    page = _switch_from_a_to_b(
        qapp,
        mocker,
        tmp_path,
        a_schedule=dict(
            schedule_mode='interval',
            schedule_interval_unit='hours',
            schedule_interval_count=3,
            schedule_fixed_hour=2,
            schedule_fixed_minute=0,
        ),
        b_schedule=dict(
            schedule_mode='fixed',
            schedule_interval_unit='days',
            schedule_interval_count=2,
            schedule_fixed_hour=23,
            schedule_fixed_minute=0,
        ),
        b_last_run=dt(2020, 5, 5, 23, 0),
    )
    assert page.scheduleFixedRadio.isChecked()
    assert page.frameDaily.isEnabled() and not page.framePeriodic.isEnabled()


def test_repo_change_refreshes_next_backup_label_without_rearming(qapp, mocker):
    page = qapp.main_window.scheduleTab.schedulePage
    page.nextBackupDateTimeLabel.setText('stale')
    spy = mocker.spy(qapp.scheduler, 'set_timer_for_profile')
    qapp.main_window.repoTab.repo_changed.emit()
    assert page.nextBackupDateTimeLabel.text() != 'stale'
    spy.assert_not_called()


def test_schedule_edits_after_populate_still_save(qapp, mocker):
    mocker.patch.object(qapp.scheduler, 'create_backup')
    page = qapp.main_window.scheduleTab.schedulePage
    spy = mocker.spy(qapp.scheduler, 'set_timer_for_profile')
    page.scheduleIntervalRadio.click()
    page.scheduleIntervalUnit.setCurrentIndex(page.scheduleIntervalUnit.findData('days'))
    page.scheduleIntervalCount.setValue(7)
    page.scheduleFixedTime.setTime(QtCore.QTime(5, 6))
    assert _schedule_row(BackupProfileModel.get(name=PROFILE_NAME).id) == ('interval', 'days', 7, 5, 6)
    assert spy.call_count == 4


def test_import_over_current_profile_rearms_its_timer(qapp, qtbot, mocker, monkeypatch, clockmock, tmp_path):
    mocker.patch.object(qapp.scheduler, 'create_backup')
    wait_for_workers(qapp.jobs_manager)
    now = dt(2020, 5, 6, 12, 0)
    clockmock.now.return_value = now
    main = qapp.main_window
    page = main.scheduleTab.schedulePage

    profile = BackupProfileModel.get(name=PROFILE_NAME)
    profile.schedule_mode = 'interval'
    profile.schedule_interval_unit = 'hours'
    profile.schedule_interval_count = 1
    profile.save()
    EventLogModel.create(
        subcommand='create',
        category='scheduled',
        profile=profile.id,
        returncode=0,
        start_time=now,
        end_time=now,
    )
    qapp.profile_changed_event.emit()
    qapp.scheduler.set_timer_for_profile(profile.id)
    assert qapp.scheduler.next_job_for_profile(profile.id).time == now + timedelta(hours=1)
    label_before = page.nextBackupDateTimeLabel.text()

    export = ProfileExport.from_db(BackupProfileModel.get(id=profile.id), store_password=False)
    export._profile_dict['schedule_interval_unit'] = 'days'
    export._profile_dict['schedule_interval_count'] = 5
    export_file = tmp_path / 'export.json'
    export_file.write_text(export.to_json())

    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *args: [str(export_file)])
    monkeypatch.setattr(QMessageBox, 'information', lambda *args: None)
    main.profile_import_action()
    import_dialog = main.window
    import_dialog.overwriteExistingProfile.setChecked(True)
    import_dialog.overwriteExistingSettings.setChecked(False)
    qtbot.mouseClick(
        import_dialog.buttonBox.button(QDialogButtonBox.StandardButton.Ok), QtCore.Qt.MouseButton.LeftButton
    )

    assert _schedule_row(profile.id)[1:3] == ('days', 5)
    assert page.scheduleIntervalUnit.currentData() == 'days'
    assert page.scheduleIntervalCount.value() == 5
    assert qapp.scheduler.next_job_for_profile(profile.id).time == now + timedelta(days=5)
    assert page.nextBackupDateTimeLabel.text() != label_before
