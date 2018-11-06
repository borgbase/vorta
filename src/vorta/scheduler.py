from datetime import date, timedelta
from apscheduler.schedulers.qt import QtScheduler
from apscheduler.triggers import cron

from vorta.borg.create import BorgCreateThread
from .models import BackupProfileMixin, EventLogModel
from vorta.borg.prune import BorgPruneThread
from vorta.borg.list import BorgListThread
from vorta.borg.check import BorgCheckThread
from .notifications import VortaNotifications


class VortaScheduler(QtScheduler, BackupProfileMixin):
    def __init__(self, parent):
        super().__init__()
        self.app = parent
        self.start()
        self.reload()

    def reload(self):
        profile = self.profile()

        trigger = None
        if profile.schedule_mode == 'interval':
            trigger = cron.CronTrigger(hour=f'*/{self.profile().schedule_interval_hours}',
                                       minute=profile.schedule_interval_minutes)
        elif profile.schedule_mode == 'fixed':
            trigger = cron.CronTrigger(hour=profile.schedule_fixed_hour,
                                       minute=profile.schedule_fixed_minute)

        if self.get_jobs() and trigger is not None:
            self.reschedule_job('create-backup', trigger=trigger)
            notifier = VortaNotifications.pick()()
            notifier.deliver('Vorta Scheduler', 'New schedule was successfully applied.')
        elif trigger is not None:
            self.add_job(func=self.create_backup, trigger=trigger, id='create-backup', misfire_grace_time=180)
        else:
            self.remove_all_jobs()

    @property
    def next_job(self):
        job = self.get_job('create-backup')
        if job is None:
            return 'Manual Backups'
        else:
            return job.next_run_time.strftime('%Y-%m-%d %H:%M')

    def create_backup(self):
        notifier = VortaNotifications.pick()()
        msg = BorgCreateThread.prepare(self.profile())
        if msg['ok']:
            thread = BorgCreateThread(msg['cmd'], msg)
            thread.start()
            thread.wait()
            if thread.process.returncode == 0:
                self.post_backup_tasks()
            else:
                notifier.deliver('Vorta Backup', 'Error during backup creation.')
        else:
            notifier.deliver('Vorta Backup', msg['message'])

    def post_backup_tasks(self):
        """
        Pruning and checking after successful backup.
        """
        profile = self.profile()
        if profile.prune_on:
            msg = BorgPruneThread.prepare(profile)
            if msg['ok']:
                prune_thread = BorgPruneThread(msg['cmd'], msg)
                prune_thread.start()
                prune_thread.wait()

                # Refresh snapshots
                msg = BorgListThread.prepare(profile)
                if msg['ok']:
                    list_thread = BorgListThread(msg['cmd'], msg)
                    list_thread.start()
                    list_thread.wait()

        validation_cutoff = date.today() - timedelta(days=7*profile.validation_weeks)
        recent_validations = EventLogModel.select().where(
            (EventLogModel.subcommand == 'check')
            & (EventLogModel.start_time > validation_cutoff)
            & (EventLogModel.repo_url == profile.repo.url)
        ).count()
        if profile.validation_on and recent_validations == 0:
            msg = BorgCheckThread.prepare(profile)
            if msg['ok']:
                check_thread = BorgCheckThread(msg['cmd'], msg)
                check_thread.start()
                check_thread.wait()
