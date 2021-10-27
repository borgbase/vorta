from datetime import datetime as dt, date, time
from PyQt5 import QtCore


def test_schedule_tab(qapp, qtbot):
    main = qapp.main_window
    tab = main.scheduleTab
    qtbot.mouseClick(tab.scheduleOffRadio, QtCore.Qt.LeftButton)
    assert tab.nextBackupDateTimeLabel.text() == 'None scheduled'

    tab.scheduleIntervalCount.setValue(5)
    qtbot.mouseClick(tab.scheduleIntervalRadio, QtCore.Qt.LeftButton)
    assert "None" not in tab.nextBackupDateTimeLabel.text()

    tab.scheduleFixedTime.setTime(QtCore.QTime(23, 59))
    qtbot.mouseClick(tab.scheduleFixedRadio, QtCore.Qt.LeftButton)
    next_backup = dt.combine(date.today(), time(23, 59))
    assert tab.nextBackupDateTimeLabel.text() == next_backup.strftime('%Y-%m-%d %H:%M')
