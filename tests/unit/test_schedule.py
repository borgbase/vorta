from datetime import datetime as dt
from datetime import timedelta
from unittest.mock import MagicMock

import pytest
import vorta.scheduler
from PyQt6 import QtCore
from vorta.application import VortaApp
from vorta.store.models import BackupProfileModel, EventLogModel

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
    qapp.scheduler.schedule_changed.connect(lambda *args: tab.draw_next_scheduled_backup())

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
