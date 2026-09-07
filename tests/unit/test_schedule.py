from datetime import datetime as dt
from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from PyQt6 import QtCore
from PyQt6.QtWidgets import QWidget

import vorta.scheduler
from vorta.application import VortaApp
from vorta.store.models import BackupProfileModel, EventLogModel, JobModel
from vorta.views.partials.jobs_table_model import JobsTableModel
from vorta.views.schedule_tab import ScheduleTab

PROFILE_NAME = 'Default'


@pytest.fixture
def clockmock(monkeypatch):
    datetime_mock = MagicMock(wraps=dt)
    monkeypatch.setattr(vorta.scheduler, "dt", datetime_mock)

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
