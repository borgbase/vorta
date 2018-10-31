from apscheduler.schedulers.qt import QtScheduler
from apscheduler.triggers import cron

from .borg_runner import BorgThread
from .models import BackupProfileMixin



class VortaScheduler(QtScheduler, BackupProfileMixin):
    def __init__(self, parent):
        super().__init__()
        self.app = parent
        self.start()
        self.reload()

    def reload(self):
        self.remove_all_jobs()
        if self.profile.schedule_mode == 'off':
            self.next_job = 'Manual Backups'
            return None
        elif self.profile.schedule_mode == 'interval':
            trigger = cron.CronTrigger(hour=f'*/{profile.schedule_interval_hours}',
                                       minute=self.profile.schedule_interval_minutes)
        elif self.profile.schedule_mode == 'fixed':
            trigger = cron.CronTrigger(hour=self.profile.schedule_fixed_hour,
                                       minute=self.profile.schedule_fixed_minute)

        self.add_job(self.create_backup, trigger, id='create-backup', misfire_grace_time=180)

    @property
    def next_job(self):
        job = self.get_job('create-backup')
        return job.next_run_time.strftime('%Y-%m-%d %H:%M')

    @classmethod
    def create_backup(cls):
        msg = BorgThread.prepare_runner()
        if msg['ok']:
            thread = BorgThread(msg['cmd'], msg['params'])
            thread.start()
            thread.wait()
