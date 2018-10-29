from apscheduler.schedulers.qt import QtScheduler
from apscheduler.triggers import cron

def tick():
    print('scheduler')

def init_scheduler():
    s = QtScheduler()
    trigger = cron.CronTrigger(second='*/3')
    s.add_job(tick, trigger, id='create-backup')
    s.start()
    return s
