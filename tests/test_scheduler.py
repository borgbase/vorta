from datetime import datetime as dt
from datetime import timedelta as td
from functools import wraps
from unittest.mock import MagicMock

import pytest
import vorta.borg
import vorta.scheduler
from pytest import mark
from vorta.scheduler import ScheduleStatus, ScheduleStatusType, VortaScheduler
from vorta.store.models import BackupProfileModel, EventLogModel

PROFILE_NAME = 'Default'
FIXED_SCHEDULE = 'fixed'
INTERVAL_SCHEDULE = 'interval'
MANUAL_SCHEDULE = 'off'


@pytest.fixture
def clockmock(monkeypatch):
    datetime_mock = MagicMock(wraps=dt)
    monkeypatch.setattr(vorta.scheduler, "dt", datetime_mock)

    return datetime_mock


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
