import enum
import logging
import threading
from datetime import datetime as dt
from datetime import timedelta
from typing import Dict, NamedTuple, Optional, Tuple, Union

from PyQt6 import QtCore, QtDBus
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from vorta import application
from vorta.borg.check import BorgCheckJob
from vorta.borg.create import BorgCreateJob
from vorta.borg.list_repo import BorgListRepoJob
from vorta.borg.prune import BorgPruneJob
from vorta.i18n import translate
from vorta.notifications import VortaNotifications
from vorta.store.models import BackupProfileModel, EventLogModel

logger = logging.getLogger(__name__)


class ScheduleStatusType(enum.Enum):
    SCHEDULED = enum.auto()  # date provided
    UNSCHEDULED = enum.auto()  # Unknown
    TOO_FAR_AHEAD = enum.auto()  # QTimer range exceeded, date provided
    NO_PREVIOUS_BACKUP = enum.auto()  # run a manual backup first


class ScheduleStatus(NamedTuple):
    type: ScheduleStatusType
    time: Optional[dt] = None


class VortaScheduler(QtCore.QObject):
    #: The schedule for the profile with the given id changed.
    schedule_changed = QtCore.pyqtSignal(int)

    def __init__(self):
        super().__init__()

        #: mapping of profiles to timers
        self.timers: Dict[int, Dict[str, Union[Optional[QTimer], Optional[dt], ScheduleStatusType]]] = dict()

        self.app: application.VortaApp = QApplication.instance()
        self.lock = threading.Lock()

        # pausing will prevent scheduling for a specified time
        self.pauses: Dict[int, Tuple[dt, QtCore.QTimer]] = dict()

        # Set additional timer to make sure background tasks stay scheduled.
        # E.g. after hibernation
        self.qt_timer = QTimer()
        self.qt_timer.timeout.connect(self.reload_all_timers)
        self.qt_timer.setInterval(15 * 60 * 1000)
        self.qt_timer.start()

        # connect signals
        self.app.backup_finished_event.connect(lambda res: self.set_timer_for_profile(res['params']['profile_id']))

        # connect to `systemd-logind` to receive sleep/resume events
        # The signal `PrepareForSleep` will be emitted before and after hibernation.
        service = "org.freedesktop.login1"
        path = "/org/freedesktop/login1"
        interface = "org.freedesktop.login1.Manager"
        name = "PrepareForSleep"
        bus = QtDBus.QDBusConnection.systemBus()
        if bus.isConnected() and bus.interface().isServiceRegistered(service).value():
            self.bus = bus
            self.bus.connect(service, path, interface, name, "b", self.loginSuspendNotify)
        else:
            logger.warn('Failed to connect to DBUS interface to detect sleep/resume events')

    @QtCore.pyqtSlot(bool)
    def loginSuspendNotify(self, suspend: bool):
        if not suspend:
            logger.debug("Got login suspend/resume notification")
            self.reload_all_timers()

    def tr(self, *args, **kwargs):
        scope = self.__class__.__name__
        return translate(scope, *args, **kwargs)

    def pause(self, profile_id: int, until: Optional[dt] = None):
        """
        Call a timeout for scheduling of a given profile.

        If `until` is omitted, a default time for the break is calculated.

        .. warning::
            This method won't work correctly when called from a non-`QThread`.


        Parameters
        ----------
        profile_id : int
            The profile to pause the scheduling for.
        until : Optional[dt], optional
            The time to end the pause, by default None
        """
        profile = BackupProfileModel.get_or_none(id=profile_id)
        if profile is None:  # profile doesn't exist any more.
            return

        if profile.schedule_mode == 'off':
            return

        if until is None:
            # calculate default timeout

            if profile.schedule_mode == 'interval':
                interval = timedelta(**{profile.schedule_interval_unit: profile.schedule_interval_count})
            else:
                # fixed
                interval = timedelta(days=1)

            timeout = interval // 6  # 60 / 6 = 10 [min]
            timeout = max(min(timeout, timedelta(hours=1)), timedelta(minutes=1))  # 1 <= t <= 60

            until = dt.now().replace(microsecond=0) + timeout
        elif until < dt.now():
            return

        # remove existing schedule
        self.remove_job(profile_id)

        # setting timer for reschedule is not possible if called
        # from a non-QThread -  it won't fail but won't work
        timer_value = max(1, (until - dt.now()).total_seconds())
        timer = QtCore.QTimer()
        timer.setInterval(int(timer_value * 1000) + 100)
        timer.timeout.connect(lambda: self.set_timer_for_profile(profile_id))
        timer.start()

        # set timeout/pause
        other_pause = self.pauses.get(profile_id)
        if other_pause is not None:
            logger.debug(f"Override existing timeout for profile {profile_id}")

        self.pauses[profile_id] = (until, timer)
        logger.debug(f"Paused {profile_id} until {until.strftime('%Y-%m-%d %H:%M:%S')}")

    def unpause(self, profile_id: int):
        """
        Return to scheduling for a profile.

        Parameters
        ----------
        profile_id : int
            The profile to end the timeout for.
        """
        profile = BackupProfileModel.get_or_none(id=profile_id)
        if profile is None:  # profile doesn't exist any more.
            return

        pause = self.pauses.get(profile_id)
        if pause is None:  # already unpaused
            return

        dummy, timer = pause
        timer.stop()
        del self.pauses[profile_id]

        logger.debug(f"Unpaused {profile_id}")

        self.set_timer_for_profile(profile_id)

    def paused(self, profile_id: int) -> bool:
        """
        Determine whether scheduling for a profile is paused

        Parameters
        ----------
        profile_id : int

        Returns
        -------
        bool
        """
        return self.pauses.get(profile_id) is not None

    def set_timer_for_profile(self, profile_id: int):
        """
        Set a timer for next scheduled backup run of this profile.

        Removes existing jobs if set to manual only or no repo is assigned.

        Else will look for previous scheduled backups and catch up if
        schedule_make_up_missed is enabled.

        Or, if catch-up is not enabled, will add interval to last run to find
        next suitable backup time.
        """
        profile = BackupProfileModel.get_or_none(id=profile_id)
        if profile is None:  # profile doesn't exist any more.
            return

        with self.lock:  # Acquire lock
            self.remove_job(profile_id)  # reset schedule

            pause = self.pauses.get(profile_id)
            if pause is not None:
                pause_end, timer = pause
                if dt.now() < pause_end:
                    logger.debug(
                        'Nothing scheduled for profile %s ' + 'because of timeout until %s.',
                        profile_id,
                        pause[0].strftime('%Y-%m-%d %H:%M:%S'),
                    )
                    return
                else:
                    timer.stop()
                    del self.pauses[profile_id]

            if profile.repo is None:  # No backups without repo set
                logger.debug(
                    'Nothing scheduled for profile %s because of unset repo.',
                    profile_id,
                )
                # Emit signal so that e.g. the GUI can react to the new schedule
                self.schedule_changed.emit(profile_id)
                return

            if profile.schedule_mode == 'off':
                logger.debug('Scheduler for profile %s is disabled.', profile_id)
                # Emit signal so that e.g. the GUI can react to the new schedule
                self.schedule_changed.emit(profile_id)
                return

            logger.info('Setting timer for profile %s', profile_id)

            # determine last backup time
            last_run_log = (
                EventLogModel.select()
                .where(
                    EventLogModel.subcommand == 'create',
                    EventLogModel.category == 'scheduled',
                    EventLogModel.profile == profile.id,
                    0 <= EventLogModel.returncode <= 1,
                )
                .order_by(EventLogModel.end_time.desc())
                .first()
            )

            if last_run_log is None:
                # look for non scheduled (manual) backup runs
                last_run_log = (
                    EventLogModel.select()
                    .where(
                        EventLogModel.subcommand == 'create',
                        EventLogModel.profile == profile.id,
                        0 <= EventLogModel.returncode <= 1,
                    )
                    .order_by(EventLogModel.end_time.desc())
                    .first()
                )

            if last_run_log is None:
                logger.info(
                    f"Nothing scheduled for profile {profile_id} "
                    + "because it would be the first backup "
                    + "for this profile."
                )
                self.timers[profile_id] = {'type': ScheduleStatusType.NO_PREVIOUS_BACKUP}
                # Emit signal so that e.g. the GUI can react to the new schedule
                self.schedule_changed.emit(profile_id)
                return

            # calculate next scheduled time
            if profile.schedule_mode == 'interval':
                last_time: dt = last_run_log.end_time

                interval = {profile.schedule_interval_unit: profile.schedule_interval_count}
                next_time = last_time + timedelta(**interval)

            elif profile.schedule_mode == 'fixed':
                last_time = last_run_log.end_time

                next_time = last_time.replace(
                    hour=profile.schedule_fixed_hour,
                    minute=profile.schedule_fixed_minute,
                    second=0,
                    microsecond=0,
                ) + timedelta(days=1)

            else:
                # unknown schedule mode
                raise ValueError("Unknown schedule mode '{}'".format(profile.schedule_mode))

            # handle missing of a scheduled time
            if next_time <= dt.now():
                if profile.schedule_make_up_missed:
                    self.lock.release()
                    try:
                        logger.debug(
                            'Catching up by running job for %s (%s)',
                            profile.name,
                            profile_id,
                        )
                        self.create_backup(profile_id)
                    finally:
                        self.lock.acquire()  # with-statement will try to release

                    return  # create_backup will lead to a call to this method

                # calculate next time from now
                if profile.schedule_mode == 'interval':
                    # next_time % interval should be 0
                    # while next_time > now
                    delta = dt.now() - last_time
                    next_time = dt.now() - delta % timedelta(**interval)
                    next_time += timedelta(**interval)

                elif profile.schedule_mode == 'fixed':
                    # schedule for today
                    next_time = dt.now().replace(
                        hour=profile.schedule_fixed_hour,
                        minute=profile.schedule_fixed_minute,
                        second=0,
                        microsecond=0,
                    )

                    if next_time <= dt.now():
                        # time for today has passed, schedule for tomorrow
                        next_time += timedelta(days=1)

            # start QTimer
            timer_ms = (next_time - dt.now()).total_seconds() * 1000

            if timer_ms < 2**31 - 1:
                logger.debug('Scheduling next run for %s', next_time)

                timer = QTimer()
                timer.setSingleShot(True)
                timer.setInterval(int(timer_ms))
                timer.timeout.connect(lambda: self.create_backup(profile_id))
                timer.start()

                self.timers[profile_id] = {
                    'qtt': timer,
                    'dt': next_time,
                    'type': ScheduleStatusType.SCHEDULED,
                }
            else:
                # int to big to pass it to qt which expects a c++ int
                # wait 15 min for regular reschedule
                logger.debug(f"Couldn't schedule for {next_time} because " f"timer value {timer_ms} too large.")

                self.timers[profile_id] = {
                    'dt': next_time,
                    'type': ScheduleStatusType.TOO_FAR_AHEAD,
                }

        # Emit signal so that e.g. the GUI can react to the new schedule
        self.schedule_changed.emit(profile_id)

    def reload_all_timers(self):
        logger.debug('Refreshing all scheduler timers')
        for profile in BackupProfileModel.select():
            self.set_timer_for_profile(profile.id)

    def next_job(self):
        now = dt.now()

        def is_scheduled(timer):
            return timer["type"] == ScheduleStatusType.SCHEDULED and timer["qtt"].isActive() and timer["dt"] >= now

        scheduled = {profile_id: timer for profile_id, timer in self.timers.items() if is_scheduled(timer)}
        if len(scheduled) == 0:
            return self.tr("None scheduled")

        closest_job = min(scheduled.items(), key=lambda item: item[1]["dt"])
        profile_id, timer = closest_job
        time = timer["dt"]
        profile = BackupProfileModel.get_or_none(id=profile_id)

        time_format = "%H:%M"
        if time - now > timedelta(days=1):
            time_format = "%b %d, %H:%M"
        return f"{time.strftime(time_format)} ({profile.name})"

    def next_job_for_profile(self, profile_id: int) -> ScheduleStatus:
        job = self.timers.get(profile_id)
        if job is None:
            return ScheduleStatus(ScheduleStatusType.UNSCHEDULED)
        return ScheduleStatus(job['type'], time=job.get('dt'))

    def create_backup(self, profile_id):
        notifier = VortaNotifications.pick()
        profile = BackupProfileModel.get_or_none(id=profile_id)

        if profile is None:
            logger.info('Profile not found. Maybe deleted?')
            return

        # Skip if a job for this profile (repo) is already in progress
        if self.app.jobs_manager.is_worker_running(site=profile.repo.id):
            logger.debug('A job for repo %s is already active.', profile.repo.id)
            self.pause(profile_id)
            return

        with self.lock:
            logger.info('Starting background backup for %s', profile.name)
            notifier.deliver(
                self.tr('Vorta Backup'),
                self.tr('Starting background backup for %s.') % profile.name,
                level='info',
            )
            msg = BorgCreateJob.prepare(profile)
            if msg['ok']:
                logger.info('Preparation for backup successful.')
                msg['category'] = 'scheduled'
                job = BorgCreateJob(msg['cmd'], msg, profile.repo.id)
                job.result.connect(self.notify)
                self.app.jobs_manager.add_job(job)
            else:
                logger.error('Conditions for backup not met. Aborting.')
                logger.error(msg['message'])
                notifier.deliver(
                    self.tr('Vorta Backup'),
                    translate('messages', msg['message']),
                    level='error',
                )
                self.pause(profile_id)

    def notify(self, result):
        notifier = VortaNotifications.pick()
        profile_name = result['params']['profile_name']
        profile_id = result['params']['profile'].id

        if result['returncode'] in [0, 1]:
            notifier.deliver(
                self.tr('Vorta Backup'),
                self.tr('Backup successful for %s.') % profile_name,
                level='info',
            )
            logger.info('Backup creation successful.')
            # unpause scheduler
            self.unpause(result['params']['profile_id'])

            self.post_backup_tasks(profile_id)
        else:
            notifier.deliver(
                self.tr('Vorta Backup'),
                self.tr('Error during backup creation for %s.') % profile_name,
                level='error',
            )
            logger.error('Error during backup creation.')
            # pause scheduler
            # if a scheduled backup fails the scheduler should pause
            # temporarily.
            self.pause(result['params']['profile_id'])

        self.set_timer_for_profile(profile_id)

    def post_backup_tasks(self, profile_id):
        """
        Pruning and checking after successful backup.
        """
        profile = BackupProfileModel.get(id=profile_id)
        logger.info('Doing post-backup jobs for %s', profile.name)
        if profile.prune_on:
            msg = BorgPruneJob.prepare(profile)
            if msg['ok']:
                job = BorgPruneJob(msg['cmd'], msg, profile.repo.id)
                self.app.jobs_manager.add_job(job)

                # Refresh archives
                msg = BorgListRepoJob.prepare(profile)
                if msg['ok']:
                    job = BorgListRepoJob(msg['cmd'], msg, profile.repo.id)
                    self.app.jobs_manager.add_job(job)

        validation_cutoff = dt.now() - timedelta(days=7 * profile.validation_weeks)
        recent_validations = (
            EventLogModel.select()
            .where(
                (EventLogModel.subcommand == 'check')
                & (EventLogModel.start_time > validation_cutoff)
                & (EventLogModel.repo_url == profile.repo.url)
            )
            .count()
        )
        if profile.validation_on and recent_validations == 0:
            msg = BorgCheckJob.prepare(profile)
            if msg['ok']:
                job = BorgCheckJob(msg['cmd'], msg, profile.repo.id)
                self.app.jobs_manager.add_job(job)

        logger.info('Finished background task for profile %s', profile.name)

    def remove_job(self, profile_id):
        if profile_id in self.timers:
            qtimer = self.timers[profile_id].get('qtt')
            if qtimer is not None:
                qtimer.stop()

            del self.timers[profile_id]
