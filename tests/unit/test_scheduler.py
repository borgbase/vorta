from datetime import datetime as dt
from datetime import timedelta as td
from functools import wraps
from unittest.mock import MagicMock

import pytest
from PyQt6 import QtCore
from PyQt6.QtWidgets import QDialogButtonBox, QMessageBox
from pytest import mark

import vorta.borg
import vorta.scheduler
from vorta.scheduler import ScheduleStatus, ScheduleStatusType, VortaScheduler
from vorta.store.models import BackupProfileModel, EventLogModel, JobModel, SchedulerPauseModel

PROFILE_NAME = 'Default'
FIXED_SCHEDULE = 'fixed'
INTERVAL_SCHEDULE = 'interval'
MANUAL_SCHEDULE = 'off'


@pytest.fixture
def clockmock(monkeypatch):
    datetime_mock = MagicMock(wraps=dt)
    monkeypatch.setattr(vorta.scheduler, "dt", datetime_mock)

    return datetime_mock


@pytest.fixture(autouse=True)
def stopped_wake_timers(qapp, monkeypatch):
    """The app keeps every scheduler alive, so a tick would land in an unrelated later test."""
    qapp.scheduler.wake_timer.stop()
    original_init = VortaScheduler.__init__

    def init_with_stopped_wake_timer(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.wake_timer.stop()

    monkeypatch.setattr(VortaScheduler, '__init__', init_with_stopped_wake_timer)


def prepare(func):
    """Decorator adding common preparation steps."""

    @wraps(func)
    def do(qapp, qtbot, mocker, borg_json_output):
        stdout, stderr = borg_json_output('create')
        popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
        mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

        return func(qapp, qtbot, mocker, borg_json_output)

    return do


@prepare
def test_scheduler_create_backup(qapp, qtbot, mocker, borg_json_output):
    """Test running a backup with `create_backup`."""
    events_before = EventLogModel.select().count()

    with qtbot.waitSignal(qapp.backup_finished_event, **pytest._wait_defaults):
        qapp.scheduler.create_backup(1)

    assert EventLogModel.select().count() == events_before + 1


def test_manual_mode():
    """Test scheduling in manual mode."""
    scheduler = VortaScheduler()

    # setup model
    profile = BackupProfileModel.get(name=PROFILE_NAME)
    profile.schedule_make_up_missed = False
    profile.schedule_mode = MANUAL_SCHEDULE
    profile.save()

    # test
    scheduler.set_timer_for_profile(profile.id)
    assert len(scheduler.timers) == 0


def test_set_timer_for_missing_profile():
    """A timer firing for a deleted profile must not crash the scheduler."""
    scheduler = VortaScheduler()

    missing_id = (BackupProfileModel.select().count() or 0) + 1000
    assert BackupProfileModel.get_or_none(id=missing_id) is None

    # Should return quietly instead of raising AttributeError on None.
    scheduler.set_timer_for_profile(missing_id)
    assert len(scheduler.timers) == 0


def test_pause_survives_restart():
    """A pause is restored when the scheduler is recreated, and unpause clears it."""
    profile = BackupProfileModel.get(name=PROFILE_NAME)
    profile.schedule_mode = INTERVAL_SCHEDULE
    profile.save()

    VortaScheduler().pause(profile.id)
    stored = SchedulerPauseModel.get_or_none(profile=profile.id)
    assert stored is not None

    restarted = VortaScheduler()
    assert restarted.paused(profile.id)
    assert restarted.next_job_for_profile(profile.id) == ScheduleStatus(ScheduleStatusType.PAUSED, stored.paused_until)

    restarted.unpause(profile.id)
    assert restarted.next_job_for_profile(profile.id).type is not ScheduleStatusType.PAUSED
    assert SchedulerPauseModel.get_or_none(profile=profile.id) is None


def test_expired_pause_dropped_on_restart(clockmock):
    """A pause that ran out while Vorta was closed must not keep blocking the schedule."""
    profile = BackupProfileModel.get(name=PROFILE_NAME)
    profile.schedule_mode = INTERVAL_SCHEDULE
    profile.save()

    SchedulerPauseModel.replace(profile=profile.id, paused_until=dt(2020, 5, 6, 4, 30)).execute()
    clockmock.now.return_value = dt(2020, 5, 6, 5, 30)

    scheduler = VortaScheduler()

    assert not scheduler.paused(profile.id)
    assert SchedulerPauseModel.get_or_none(profile=profile.id) is None


def test_pause_cleared_when_it_runs_out(clockmock):
    """A pause running out while Vorta stays open clears the row and reschedules."""
    profile = BackupProfileModel.get(name=PROFILE_NAME)
    profile.schedule_mode = INTERVAL_SCHEDULE
    profile.save()

    clockmock.now.return_value = dt(2020, 5, 6, 4, 30)
    scheduler = VortaScheduler()
    scheduler.pause(profile.id)

    clockmock.now.return_value = dt(2020, 5, 6, 6, 30)
    scheduler.set_timer_for_profile(profile.id)

    assert not scheduler.paused(profile.id)
    assert SchedulerPauseModel.get_or_none(profile=profile.id) is None


def test_deleting_a_paused_profile_clears_the_pause(qapp, qtbot, mocker):
    """SQLite reuses ids, so a new profile must not inherit a deleted one's pause."""
    main = qapp.main_window
    main.profile_add_action()
    qtbot.keyClicks(main.window.profileNameField, 'Paused Profile')
    qtbot.mouseClick(
        main.window.buttonBox.button(QDialogButtonBox.StandardButton.Save), QtCore.Qt.MouseButton.LeftButton
    )

    profile = BackupProfileModel.get(name='Paused Profile')
    profile.schedule_mode = INTERVAL_SCHEDULE
    profile.save()
    qapp.scheduler.pause(profile.id)
    assert SchedulerPauseModel.get_or_none(profile=profile.id) is not None

    mocker.patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes)
    qtbot.mouseClick(main.profileDeleteButton, QtCore.Qt.MouseButton.LeftButton)

    assert not qapp.scheduler.paused(profile.id)
    assert SchedulerPauseModel.get_or_none(profile=profile.id) is None


def test_paused_manual_profile_reports_unscheduled():
    """Switching a paused profile to manual reports no schedule, not a pause."""
    profile = BackupProfileModel.get(name=PROFILE_NAME)
    profile.schedule_mode = INTERVAL_SCHEDULE
    profile.save()

    scheduler = VortaScheduler()
    scheduler.pause(profile.id)

    profile.schedule_mode = MANUAL_SCHEDULE
    profile.save()
    scheduler.set_timer_for_profile(profile.id)

    assert scheduler.paused(profile.id)
    assert scheduler.next_job_for_profile(profile.id).type is ScheduleStatusType.UNSCHEDULED
    assert VortaScheduler().next_job_for_profile(profile.id).type is ScheduleStatusType.UNSCHEDULED


def test_simple_schedule(clockmock):
    """Test a simple scheduling including `next_job` and `remove_job`."""
    scheduler = VortaScheduler()

    # setup
    time = dt(2020, 5, 6, 4, 30)
    clockmock.now.return_value = time

    profile = BackupProfileModel.get(name=PROFILE_NAME)
    profile.schedule_make_up_missed = False
    profile.schedule_mode = INTERVAL_SCHEDULE
    profile.schedule_interval_unit = 'hours'
    profile.schedule_interval_count = 3
    profile.save()

    event = EventLogModel(
        subcommand='create', profile=profile.id, returncode=0, category='scheduled', start_time=time, end_time=time
    )
    event.save()

    # test set timer and next_job
    scheduler.set_timer_for_profile(profile.id)
    assert len(scheduler.timers) == 1
    assert scheduler.next_job() == '07:30 ({})'.format(PROFILE_NAME)
    assert scheduler.next_job_for_profile(profile.id) == ScheduleStatus(
        ScheduleStatusType.SCHEDULED, dt(2020, 5, 6, 7, 30)
    )

    # test remove_job and next_job
    scheduler.remove_job(profile.id)
    assert len(scheduler.timers) == 0
    assert scheduler.next_job() == 'None scheduled'
    assert scheduler.next_job_for_profile(profile.id) == ScheduleStatus(ScheduleStatusType.UNSCHEDULED)


@mark.parametrize("scheduled", [True, False])
@mark.parametrize(
    "passed_time, now, unit, count, added_time",
    [
        # simple
        (td(), td(hours=4, minutes=30), 'hours', 3, td(hours=3)),
        # next day
        (td(), td(hours=4, minutes=30), 'hours', 20, td(hours=20)),
        # passed by less than interval
        (td(hours=2), td(hours=4, minutes=30), 'hours', 3, td(hours=1)),
        # passed by exactly interval
        (td(hours=3), td(hours=4, minutes=30), 'hours', 3, td(hours=3)),
        # passed by multiple times the interval
        (td(hours=7), td(hours=4, minutes=30), 'hours', 3, td(hours=2)),
    ],
)
def test_interval(clockmock, passed_time, scheduled, now, unit, count, added_time):
    """Test scheduling in interval mode."""
    # setup
    scheduler = VortaScheduler()

    time = dt(2020, 5, 4, 0, 0) + now
    clockmock.now.return_value = time

    profile = BackupProfileModel.get(name=PROFILE_NAME)
    profile.schedule_make_up_missed = False
    profile.schedule_mode = INTERVAL_SCHEDULE
    profile.schedule_interval_unit = unit
    profile.schedule_interval_count = count
    profile.save()

    event = EventLogModel(
        subcommand='create',
        profile=profile.id,
        returncode=0,
        category='scheduled' if scheduled else '',
        start_time=time - passed_time,
        end_time=time - passed_time,
    )
    event.save()

    # run test
    scheduler.set_timer_for_profile(profile.id)
    assert scheduler.timers[profile.id]['dt'] == time + added_time


@mark.parametrize("scheduled", [True, False])
@mark.parametrize("passed_time", [td(hours=0), td(hours=5), td(hours=14), td(hours=27)])
@mark.parametrize(
    "now, hour, minute",
    [
        # same day
        (td(hours=4, minutes=30), 15, 00),
        # next day
        (td(hours=4, minutes=30), 3, 30),
    ],
)
def test_fixed(clockmock, passed_time, scheduled, now, hour, minute):
    """Test scheduling in fixed mode."""
    # setup
    scheduler = VortaScheduler()

    time = dt(2020, 5, 4, 0, 0) + now
    clockmock.now.return_value = time

    profile = BackupProfileModel.get(name=PROFILE_NAME)
    profile.schedule_make_up_missed = False
    profile.schedule_mode = FIXED_SCHEDULE
    profile.schedule_fixed_hour = hour
    profile.schedule_fixed_minute = minute
    profile.save()

    last_time = time - passed_time
    event = EventLogModel(
        subcommand='create',
        profile=profile.id,
        returncode=0,
        category='scheduled' if scheduled else '',
        start_time=last_time,
        end_time=last_time,
    )
    event.save()

    # run test
    expected = time.replace(hour=hour, minute=minute)

    if time >= expected or last_time.date() == expected.date():
        expected += td(days=1)

    scheduler.set_timer_for_profile(profile.id)
    assert scheduler.timers[profile.id]['dt'] == expected


@mark.parametrize(
    "now, hour, minute, time_since_last_run, expect_catchup",
    [
        (td(hours=9), 18, 00, td(hours=12), False),
        (td(hours=9), 18, 00, td(hours=24), False),
        (td(hours=9), 18, 00, td(hours=36), True),
        (td(hours=20), 18, 00, td(hours=2), False),
        (td(hours=20), 18, 00, td(hours=24), True),
    ],
)
def test_missed_startup(qapp, qtbot, window_load, clockmock, now, hour, minute, time_since_last_run, expect_catchup):
    time = dt(2020, 5, 4, 0, 0) + now
    clockmock.now.return_value = time

    profile = BackupProfileModel.get(name=PROFILE_NAME)
    profile.schedule_make_up_missed = True
    profile.schedule_mode = FIXED_SCHEDULE
    profile.schedule_fixed_hour = hour
    profile.schedule_fixed_minute = minute
    profile.save()

    last_time = time - time_since_last_run
    event = EventLogModel(
        subcommand='create',
        profile=profile.id,
        returncode=0,
        category='scheduled',
        start_time=last_time,
        end_time=last_time,
    )
    event.save()

    # We have to replace the scheduler because of shared state (namely, pauses)
    # We also reload because app init does that (via `set_borg_details_result`)
    qapp.scheduler = VortaScheduler()
    qapp.scheduler.reload_all_timers()
    window_load()

    qtbot.waitSignal(qapp.main_window.loaded, **pytest._wait_defaults)

    event_times = [log.start_time for log in EventLogModel.select()]

    if expect_catchup:
        assert len(event_times) == 2
    else:
        assert len(event_times) == 1


@prepare
def test_create_backup_no_error_notification_on_info_level(qapp, qtbot, mocker, borg_json_output):
    """Test that notifier.deliver() is not called with level='error' when
    prepare() returns level='info' (e.g. WiFi disallowed or metered connection)."""
    mocker.patch(
        'vorta.scheduler.BorgCreateJob.prepare',
        return_value={
            'ok': False,
            'message': 'Current Wifi is not allowed.',
            'level': 'info',
        },
    )
    notifier_mock = mocker.patch('vorta.notifications.VortaNotifications.pick')
    mock_notifier = mocker.MagicMock()
    notifier_mock.return_value = mock_notifier

    qapp.scheduler.create_backup(1)
    # The error notification should be suppressed for an expected skip.
    assert mock_notifier.deliver.call_count == 1
    assert mock_notifier.deliver.call_args.kwargs.get('level') != 'error'


def test_create_backup_records_skip_reason(qapp, qtbot, mocker):
    """A skipped scheduled backup is recorded as a JobModel row with its reason."""
    mocker.patch(
        'vorta.scheduler.BorgCreateJob.prepare',
        return_value={
            'ok': False,
            'message': 'Current Wifi is not allowed.',
            'level': 'info',
        },
    )
    jobs_before = JobModel.select().count()

    qapp.scheduler.create_backup(1)

    assert JobModel.select().count() == jobs_before + 1
    job = JobModel.select().order_by(JobModel.id.desc()).get()
    assert job.status == JobModel.Status.SKIPPED.value
    assert job.reason == 'Current Wifi is not allowed.'
    assert job.profile == '1'
    assert job.profile_name == PROFILE_NAME


def test_create_backup_records_failure_not_skip(qapp, qtbot, mocker):
    """An unexpected prepare() failure is recorded as failed, not skipped."""
    mocker.patch(
        'vorta.scheduler.BorgCreateJob.prepare',
        return_value={
            'ok': False,
            'message': 'Add a backup repository first.',
        },
    )
    jobs_before = JobModel.select().count()

    qapp.scheduler.create_backup(1)

    assert JobModel.select().count() == jobs_before + 1
    job = JobModel.select().order_by(JobModel.id.desc()).get()
    assert job.status == JobModel.Status.FAILED.value
    assert job.reason == 'Add a backup repository first.'


def test_create_backup_records_skip_when_repo_busy(qapp, mocker):
    """A scheduled run blocked by a busy repo is recorded as a skipped JobModel row."""
    mocker.patch.object(qapp.jobs_manager, 'is_worker_running', return_value=True)
    jobs_before = JobModel.select().count()

    qapp.scheduler.create_backup(1)

    assert JobModel.select().count() == jobs_before + 1
    job = JobModel.select().order_by(JobModel.id.desc()).get()
    assert job.status == JobModel.Status.SKIPPED.value
    assert job.reason == 'Repository is busy with another job.'


def test_create_backup_keeps_the_catchup_trigger(qapp, mocker):
    """A catch-up run that gets skipped is not recorded as an ordinary scheduled run."""
    mocker.patch.object(qapp.jobs_manager, 'is_worker_running', return_value=True)

    qapp.scheduler.create_backup(1, trigger=JobModel.Trigger.CATCHUP.value)

    job = JobModel.select().order_by(JobModel.id.desc()).get()
    assert job.trigger == JobModel.Trigger.CATCHUP.value


def test_set_timer_records_skip_when_network_down_for_catchup(clockmock):
    """A catch-up run blocked by a down network is recorded as a skipped JobModel row."""
    scheduler = VortaScheduler()
    scheduler._net_up = False

    time = dt(2020, 5, 6, 4, 30)
    clockmock.now.return_value = time

    profile = BackupProfileModel.get(name=PROFILE_NAME)
    profile.schedule_make_up_missed = True
    profile.schedule_mode = INTERVAL_SCHEDULE
    profile.schedule_interval_unit = 'hours'
    profile.schedule_interval_count = 3
    profile.save()

    last_run = time - td(hours=6)
    EventLogModel.create(
        subcommand='create',
        profile=profile.id,
        returncode=0,
        category='scheduled',
        start_time=last_run,
        end_time=last_run,
    )
    jobs_before = JobModel.select().count()

    scheduler.set_timer_for_profile(profile.id)

    assert JobModel.select().count() == jobs_before + 1
    job = JobModel.select().order_by(JobModel.id.desc()).get()
    assert job.status == JobModel.Status.SKIPPED.value
    assert job.trigger == JobModel.Trigger.CATCHUP.value
    assert job.reason == 'Network unavailable for catch-up.'
    assert job.scheduled_at == last_run + td(hours=3)

    # Re-evaluating the same missed run must not add a second row.
    scheduler.set_timer_for_profile(profile.id)
    assert JobModel.select().count() == jobs_before + 1


def test_wall_clock_gap_is_treated_as_a_resume(mocker, clockmock):
    """Without logind, a jump in wall clock time is the only sign that the machine slept."""
    clockmock.now.return_value = dt(2020, 5, 6, 4, 0)
    scheduler = VortaScheduler()
    reload_all = mocker.patch.object(scheduler, 'reload_all_timers')
    scheduler.net_status = MagicMock()
    scheduler.net_status.is_network_active.return_value = True
    scheduler._net_up = False

    clockmock.now.return_value = dt(2020, 5, 6, 6, 0)
    scheduler.wake_timer.timeout.emit()

    reload_all.assert_called_once()
    assert scheduler._net_up is True


def test_timely_wake_check_does_not_reschedule(mocker, clockmock):
    """An on-time check must do nothing, or every profile gets rescheduled on every tick."""
    clockmock.now.return_value = dt(2020, 5, 6, 4, 0)
    scheduler = VortaScheduler()
    reload_all = mocker.patch.object(scheduler, 'reload_all_timers')

    clockmock.now.return_value = dt(2020, 5, 6, 4, 1)
    scheduler.wake_timer.timeout.emit()

    reload_all.assert_not_called()


def test_logind_resume_signal_reloads_timers(mocker, clockmock):
    """The logind fast path must survive the resume body moving into a helper."""
    clockmock.now.return_value = dt(2020, 5, 6, 4, 0)
    scheduler = VortaScheduler()
    reload_all = mocker.patch.object(scheduler, 'reload_all_timers')
    scheduler.net_status = MagicMock()

    scheduler.loginSuspendNotify(True)
    reload_all.assert_not_called()

    scheduler.loginSuspendNotify(False)
    reload_all.assert_called_once()
