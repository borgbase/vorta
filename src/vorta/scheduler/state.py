from __future__ import annotations

import logging
from datetime import datetime as dt
from datetime import timedelta
from typing import TYPE_CHECKING

import peewee as pw
from PyQt6 import QtCore, QtDBus
from PyQt6.QtCore import QTimer

from vorta.scheduler.scheduling import ScheduleStatusType, arm_deadline_timer
from vorta.store.models import BackupProfileModel, JobModel, SchedulerPauseModel

if TYPE_CHECKING:
    from vorta.scheduler import VortaScheduler

logger = logging.getLogger(__name__)

WAKE_CHECK_INTERVAL_MS = 5 * 60 * 1000
WAKE_GAP_THRESHOLD = timedelta(minutes=10)


class SchedulerState:
    """Pauses, recorded job outcomes and resume detection."""

    def __init__(self, scheduler: VortaScheduler) -> None:
        self.scheduler = scheduler

        # pausing will prevent scheduling for a specified time
        self.pauses: dict[int, tuple[dt, QtCore.QTimer]] = dict()

        # connect to `systemd-logind` to receive sleep/resume events
        # The signal `PrepareForSleep` will be emitted before and after hibernation.
        service = "org.freedesktop.login1"
        path = "/org/freedesktop/login1"
        interface = "org.freedesktop.login1.Manager"
        name = "PrepareForSleep"
        bus = QtDBus.QDBusConnection.systemBus()
        if bus.isConnected() and bus.interface().isServiceRegistered(service).value():
            self.bus = bus
            self.bus.connect(service, path, interface, name, "b", scheduler.loginSuspendNotify)
        else:
            logger.info('No systemd-logind to notify us of sleep/resume, watching for clock gaps as well')

        self._last_wake_check = dt.now()
        self.wake_timer = QTimer()
        self.wake_timer.timeout.connect(scheduler.checkForResume)
        self.wake_timer.setInterval(WAKE_CHECK_INTERVAL_MS)
        self.wake_timer.start()

    def loginSuspendNotify(self, suspend: bool) -> None:
        if not suspend:
            logger.debug("Got login suspend/resume notification")
            self._handle_resume()

    def checkForResume(self) -> None:
        now = dt.now()
        elapsed = now - self._last_wake_check
        self._last_wake_check = now

        if elapsed < WAKE_GAP_THRESHOLD:
            return

        logger.debug('Clock jumped %s since the last wake check, assuming the machine slept', elapsed)
        self._handle_resume()

    def _handle_resume(self) -> None:
        self._last_wake_check = dt.now()
        # Defensively refetch in case the network status didn't arrive
        self.scheduler._net_up = self.scheduler.net_status.is_network_active()
        self.scheduler.reload_all_timers()

    def pause(self, profile_id: int, until: dt | None = None) -> None:
        """
        Call a timeout for scheduling of a given profile.

        If `until` is omitted, a default time for the break is calculated.

        .. warning::
            This method won't work correctly when called from a non-`QThread`.


        Parameters
        ----------
        profile_id : int
            The profile to pause the scheduling for.
        until : dt | None, optional
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
        self.scheduler.remove_job(profile_id)

        # set timeout/pause
        other_pause = self.pauses.get(profile_id)
        if other_pause is not None:
            logger.debug(f"Override existing timeout for profile {profile_id}")

        self._set_pause(profile, until)
        logger.debug(f"Paused {profile_id} until {until.strftime('%Y-%m-%d %H:%M:%S')}")

    def _set_pause(self, profile: BackupProfileModel, until: dt) -> None:
        """Arm the reschedule timer for a pause and store it, so it outlives the process."""
        profile_id = profile.id
        replaced = self.pauses.get(profile_id)
        if replaced is not None:
            replaced[1].stop()

        # setting timer for reschedule is not possible if called
        # from a non-QThread -  it won't fail but won't work
        timer = arm_deadline_timer(until, lambda: self.scheduler.set_timer_for_profile(profile_id))

        self.pauses[profile_id] = (until, timer)

        try:
            SchedulerPauseModel.replace(profile=profile_id, paused_until=until).execute()
        except pw.PeeweeException:
            logger.warning('Could not store pause for profile %s.', profile_id, exc_info=True)

        self.scheduler.mark_paused(profile, until)

    def clear_pause(self, profile_id: int) -> None:
        """Drop a pause from memory, from the schedule status and from the database."""
        pause = self.pauses.pop(profile_id, None)
        if pause is not None:
            pause[1].stop()

        status = self.scheduler.timers.get(profile_id)
        if status is not None and status.get('type') is ScheduleStatusType.PAUSED:
            del self.scheduler.timers[profile_id]

        try:
            SchedulerPauseModel.delete().where(SchedulerPauseModel.profile == profile_id).execute()
        except pw.PeeweeException:
            logger.warning('Could not drop stored pause for profile %s.', profile_id, exc_info=True)

    def restore_pauses(self) -> None:
        """Re-arm the pauses stored by a previous run, dropping the ones that already ran out."""
        now = dt.now()

        for stored in list(SchedulerPauseModel.select()):
            profile_id = stored.profile_id
            profile = BackupProfileModel.get_or_none(id=profile_id)

            if profile is None or stored.paused_until <= now:
                self.clear_pause(profile_id)
                continue

            self._set_pause(profile, stored.paused_until)
            logger.debug(f"Restored pause for {profile_id} until {stored.paused_until:%Y-%m-%d %H:%M:%S}")

    def unpause(self, profile_id: int) -> None:
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

        self.clear_pause(profile_id)

        logger.debug(f"Unpaused {profile_id}")

        self.scheduler.set_timer_for_profile(profile_id)

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

    def record_skip(
        self,
        profile: BackupProfileModel,
        trigger: str,
        reason: str,
        status: str = JobModel.Status.SKIPPED.value,
        scheduled_at: dt | None = None,
    ) -> None:
        """Record a job outcome, deduplicated on the occurrence when one is known."""
        lookup = {
            'profile': str(profile.id),
            'trigger': trigger,
            'status': status,
            'scheduled_at': scheduled_at,
        }
        details = {
            'profile_name': profile.name,
            'repo_url': profile.repo.url if profile.repo else None,
            'job_type': JobModel.Type.BACKUP.value,
            'reason': reason,
        }

        try:
            if scheduled_at is None:
                JobModel.create(**lookup, **details)
            else:
                _, recorded = JobModel.get_or_create(**lookup, defaults=details)
                if not recorded:
                    return
        except pw.PeeweeException:
            logger.warning('Could not record job for profile %s.', profile.id, exc_info=True)
            return

        # `arm_profile` records under the scheduler's lock, and the jobs view reads the table here.
        QTimer.singleShot(0, self.scheduler.jobs_changed.emit)
