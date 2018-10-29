from apscheduler.schedulers.qt import QtScheduler

def tick():
    print('scheduler')

def init_scheduler():
    s = QtScheduler()
    s.add_job(tick, 'interval', seconds=3)
    s.start()
    return s
