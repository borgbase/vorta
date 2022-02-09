from datetime import date
from datetime import datetime as dt
from datetime import time

from PyQt5 import QtCore


def test_schedule_tab(qapp, qtbot):
    main = qapp.main_window
    tab = main.scheduleTab

    # Work around
    # because already 'deleted' scheduletabs are still connected to the signal
    qapp.scheduler.schedule_changed.disconnect()
    qapp.scheduler.schedule_changed.connect(lambda *args: tab.draw_next_scheduled_backup())

    # Test
    qtbot.mouseClick(tab.scheduleOffRadio, QtCore.Qt.LeftButton)
    assert tab.nextBackupDateTimeLabel.text() == 'None scheduled'

    tab.scheduleIntervalCount.setValue(5)
    qtbot.mouseClick(tab.scheduleIntervalRadio, QtCore.Qt.LeftButton)
    assert "None" not in tab.nextBackupDateTimeLabel.text()

    tab.scheduleFixedTime.setTime(QtCore.QTime(23, 59))
    qtbot.mouseClick(tab.scheduleFixedRadio, QtCore.Qt.LeftButton)
    next_backup = dt.combine(date.today(), time(23, 59))
    assert tab.nextBackupDateTimeLabel.text() == next_backup.strftime('%Y-%m-%d %H:%M')
