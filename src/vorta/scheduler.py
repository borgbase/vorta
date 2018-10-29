from apscheduler.schedulers.qt import QtScheduler
from apscheduler.triggers import cron
from PyQt5.QtWidgets import QApplication

from .models import BackupProfileModel


def tick():
    print('scheduler running')


def init_scheduler():
    app = QApplication.instance()
    if hasattr(app, 'scheduler') and app.scheduler is not None:
        app.scheduler.shutdown()

    s = QtScheduler()

    profile = BackupProfileModel.get(id=1)
    if profile.schedule_mode == 'off':
        return None
    elif profile.schedule_mode == 'interval':
        trigger = cron.CronTrigger(hour=f'*/{profile.schedule_interval_hours}',
                                   minute=profile.schedule_interval_minutes)
    elif profile.schedule_mode == 'fixed':
        trigger = cron.CronTrigger(hour=profile.schedule_fixed_hour,
                                   minute=profile.schedule_fixed_minute)

    s.add_job(tick, trigger, id='create-backup')
    s.start()
    return s
