from apscheduler.schedulers.qt import QtScheduler
from apscheduler.triggers import cron
from PyQt5.QtWidgets import QApplication
from PyQt5 import QtCore

from .models import BackupProfileModel, EventLogModel
from .borg_runner import BorgThread


def create_backup_task():
    msg = BorgThread.prepare_runner()
    if msg['ok']:
        t = BorgThread(None, msg['cmd'], msg['params'])
        t.start()
        t.wait()
    else:
        error_log = EventLogModel(category='borg-factory', message=msg['message'])
        error_log.save()


def init_scheduler():
    s = QtScheduler()
    app = QApplication.instance()
    if hasattr(app, 'scheduler') and app.scheduler is not None:
        app.scheduler.shutdown()

    profile = BackupProfileModel.get(id=1)
    if profile.schedule_mode == 'off':
        return None
    elif profile.schedule_mode == 'interval':
        trigger = cron.CronTrigger(hour=f'*/{profile.schedule_interval_hours}',
                                   minute=profile.schedule_interval_minutes)
    elif profile.schedule_mode == 'fixed':
        trigger = cron.CronTrigger(hour=profile.schedule_fixed_hour,
                                   minute=profile.schedule_fixed_minute)

    s.add_job(create_backup_task, trigger, id='create-backup', misfire_grace_time=180)
    s.start()
    return s
