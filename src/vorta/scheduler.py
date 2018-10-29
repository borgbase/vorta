from apscheduler.schedulers.qt import QtScheduler
from apscheduler.triggers import interval

def tick():
    print('scheduler')

def init_scheduler():
    s = QtScheduler()
    trigger = interval.IntervalTrigger(seconds=3)
    s.add_job(tick, trigger, seconds=3)
    s.start()
    return s
