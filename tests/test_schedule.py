import pytest
from datetime import datetime as dt, date, time
from PyQt5 import QtCore

from vorta.views.schedule_tab import ScheduleTab

from .fixtures import *

def test_schedule_tab(app, qtbot):
    tab = ScheduleTab(app.main_window.scheduleTabSlot)
    qtbot.mouseClick(tab.scheduleApplyButton, QtCore.Qt.LeftButton)
    assert tab.nextBackupDateTimeLabel.text() == 'Manual Backups'

    tab.scheduleIntervalRadio.setChecked(True)
    tab.scheduleIntervalHours.setValue(5)
    tab.scheduleIntervalMinutes.setValue(10)
    qtbot.mouseClick(tab.scheduleApplyButton, QtCore.Qt.LeftButton)
    assert tab.nextBackupDateTimeLabel.text().startswith('20')

    tab.scheduleOffRadio.setChecked(True)
    qtbot.mouseClick(tab.scheduleApplyButton, QtCore.Qt.LeftButton)
    assert tab.nextBackupDateTimeLabel.text() == 'Manual Backups'

    tab.scheduleFixedRadio.setChecked(True)
    tab.scheduleFixedTime.setTime(QtCore.QTime(23, 59))
    qtbot.mouseClick(tab.scheduleApplyButton, QtCore.Qt.LeftButton)
    next_backup = dt.combine(date.today(), time(23, 59))
    assert tab.nextBackupDateTimeLabel.text() == next_backup.strftime('%Y-%m-%d %H:%M')
