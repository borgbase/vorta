from apscheduler.schedulers.qt import QtScheduler
from apscheduler.triggers import cron


class VortaScheduler(QtScheduler):
    def __init__(self, parent):
        super().__init__()
        self.app = parent
        self.start()
        self.reload()

    def reload(self):
        self.remove_all_jobs()
        profile = self.app.profile
        if profile.schedule_mode == 'off':
            self.next_job = 'Manual Backups'
            return None
        elif profile.schedule_mode == 'interval':
            trigger = cron.CronTrigger(hour=f'*/{profile.schedule_interval_hours}',
                                       minute=profile.schedule_interval_minutes)
        elif profile.schedule_mode == 'fixed':
            trigger = cron.CronTrigger(hour=profile.schedule_fixed_hour,
                                       minute=profile.schedule_fixed_minute)

        self.add_job(self.app.create_backup, trigger, id='create-backup', misfire_grace_time=180)
        job = self.get_job('create-backup')
        self.next_job = f"Next run: {job.next_run_time.strftime('%Y-%m-%d %H:%M')}"
