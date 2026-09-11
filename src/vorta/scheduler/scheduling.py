from __future__ import annotations

import enum
import logging
import threading
from collections.abc import Callable
from datetime import datetime as dt
from datetime import timedelta
from typing import TYPE_CHECKING, NamedTuple

from PyQt6.QtCore import QTimer

from vorta.store.models import BackupProfileModel, EventLogModel, JobModel
from vorta.utils import get_network_status_monitor

if TYPE_CHECKING:
    from vorta.scheduler import VortaScheduler

logger = logging.getLogger(__name__)

RESCHEDULE_INTERVAL_MS = 15 * 60 * 1000

# A QTimer interval is a C++ int, so a single wait tops out at about 24.8 days.
MAX_TIMER_MS = 2**31 - 1
# Fire just after the deadline, so the handler always sees it as passed.
TIMER_GRACE_MS = 100


def arm_deadline_timer(deadline: dt, on_expiry: Callable[[], None]) -> QTimer:
    """
    Start a timer that calls `on_expiry` once `deadline` has passed.

    Waits longer than `MAX_TIMER_MS` are split into chunks, and every chunk is measured
    against the wall clock again, so the deadline holds however far ahead it is.
    """
    timer = QTimer()
    timer.setSingleShot(True)

    def remaining_ms() -> float:
        return (deadline - dt.now()).total_seconds() * 1000 + TIMER_GRACE_MS

    def rearm() -> None:
        timer.setInterval(int(max(0, min(remaining_ms(), MAX_TIMER_MS))))
        timer.start()

    def on_timeout() -> None:
        if remaining_ms() <= 0:
            on_expiry()
        else:
            rearm()

    timer.timeout.connect(on_timeout)
    rearm()
    return timer


class ScheduleStatusType(enum.Enum):
    SCHEDULED = enum.auto()  # date provided
    UNSCHEDULED = enum.auto()  # Unknown
    NO_PREVIOUS_BACKUP = enum.auto()  # run a manual backup first
    PAUSED = enum.auto()  # paused after a failed or skipped run, date provided


class ScheduleStatus(NamedTuple):
    type: ScheduleStatusType
    time: dt | None = None


#: Timer states that hold a time for a run, and the row status each one shows as.
PENDING_STATUSES = {
    ScheduleStatusType.SCHEDULED: JobModel.Status.SCHEDULED.value,
    ScheduleStatusType.PAUSED: JobModel.Status.PAUSED.value,
}


class PendingJob(NamedTuple):
    """A run the scheduler is holding a time for, but that hasn't been recorded yet."""

    profile_id: int
    profile_name: str
    repo_url: str | None
    scheduled_at: dt
    status: str


class SchedulerTimers:
    """The next run time of each profile, the timers holding them and the network gating."""

    def __init__(self, scheduler: VortaScheduler) -> None:
        self.scheduler = scheduler

        #: mapping of profiles to timers
        self.timers: dict[int, dict[str, QTimer | dt | ScheduleStatusType | None]] = dict()

        self.lock = threading.Lock()

        # Periodic reschedule, in case a run was missed
        self.qt_timer = QTimer()
        self.qt_timer.timeout.connect(scheduler.reload_all_timers)
        self.qt_timer.setInterval(RESCHEDULE_INTERVAL_MS)
        self.qt_timer.start()

        # Connect to network manager to monitor net status
        self.net_status = get_network_status_monitor()
        self.net_status.network_status_changed.connect(scheduler.networkStatusChanged)
        self._net_up = self.net_status.is_network_active()

    def networkStatusChanged(self, up: bool):
        reload = self._net_up != up
        self._net_up = up
        logger.debug(f"network status up={up}")
        if reload:
            logger.info("updating schedule due to network status change")
            self.reload_all_timers()

    def arm_profile(self, profile_id: int) -> int | None:
        """
        Set a timer for the next scheduled backup run of this profile.

        Removes existing jobs if set to manual only or no repo is assigned.

        Else will look for previous scheduled backups and catch up if
        schedule_make_up_missed is enabled.

        Or, if catch-up is not enabled, will add interval to last run to find
        next suitable backup time.

        Returns the profile id whose missed run has to be caught up, if any.
        """
        profile = BackupProfileModel.get_or_none(id=profile_id)
        if profile is None:  # profile doesn't exist any more.
            return
        logger.debug('Profile: %s, %d %d', str(profile), profile.schedule_fixed_hour, profile.schedule_fixed_minute)

        with self.lock:  # Acquire lock
            self.remove_job(profile_id)  # reset schedule

            pause = self.scheduler.pauses.get(profile_id)
            if pause is not None:
                pause_end, timer = pause
                if dt.now() < pause_end:
                    logger.debug(
                        'Nothing scheduled for profile %s ' + 'because of timeout until %s.',
                        profile_id,
                        pause[0].strftime('%Y-%m-%d %H:%M:%S'),
                    )
                    self.mark_paused(profile, pause_end)
                    return
                else:
                    self.scheduler.clear_pause(profile_id)

            if profile.repo is None:  # No backups without repo set
                logger.debug(
                    'Nothing scheduled for profile %s because of unset repo.',
                    profile_id,
                )
                # Emit signal so that e.g. the GUI can react to the new schedule
                self.scheduler.schedule_changed.emit()
                return

            if profile.schedule_mode == 'off':
                logger.debug('Scheduler for profile %s is disabled.', profile_id)
                # Emit signal so that e.g. the GUI can react to the new schedule
                self.scheduler.schedule_changed.emit()
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
                self.scheduler.schedule_changed.emit()
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

            logger.debug('Last run time: %s', last_time)

            needs_network = profile.repo is not None and profile.repo.is_remote_repo()
            # handle missing of a scheduled time
            if next_time <= dt.now():
                if profile.schedule_make_up_missed and (self._net_up or not needs_network):
                    logger.debug(
                        'Catching up by running job for %s (%s)',
                        profile.name,
                        profile_id,
                    )
                    return profile_id  # create_backup will lead to a call to this method
                elif profile.schedule_make_up_missed and not self._net_up and needs_network:
                    logger.debug('Skipping catchup %s (%s), the network is not available', profile.name, profile.id)
                    self.scheduler.record_skip(
                        profile,
                        JobModel.Trigger.CATCHUP.value,
                        'Network unavailable for catch-up.',
                        scheduled_at=next_time,
                    )

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
            logger.debug('Scheduling next run for %s', next_time)

            self.timers[profile_id] = {
                'qtt': arm_deadline_timer(next_time, lambda: self.scheduler.create_backup(profile_id)),
                'dt': next_time,
                'type': ScheduleStatusType.SCHEDULED,
            }

        # Emit signal so that e.g. the GUI can react to the new schedule
        self.scheduler.schedule_changed.emit()

    def reload_all_timers(self) -> None:
        logger.debug('Refreshing all scheduler timers')
        for profile in BackupProfileModel.select():
            # Only set a timer for the profile if the network is actually up
            if profile.repo is None:
                logger.debug("nothing scheduled for %s because of unset repo", profile.id)
            elif not profile.repo.is_remote_repo() or self._net_up:
                logger.debug("scheduling %s", profile.id)
                self.scheduler.set_timer_for_profile(profile.id)
            else:
                logger.debug("Network is down, not scheduling %s", profile.id)
                self.remove_job(profile.id)

    def next_job(self) -> str:
        now = dt.now()

        def is_scheduled(timer):
            return timer["type"] == ScheduleStatusType.SCHEDULED and timer["qtt"].isActive() and timer["dt"] >= now

        scheduled = {profile_id: timer for profile_id, timer in self.timers.items() if is_scheduled(timer)}
        if len(scheduled) == 0:
            return self.scheduler.tr("None scheduled")

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
        return ScheduleStatus(job['type'], time=job.get('dt'))  # type: ignore[arg-type]

    def pending_jobs(self) -> list[PendingJob]:
        """The runs currently on the clock, soonest first."""
        pending = []

        for profile_id, timer in self.timers.items():
            status = PENDING_STATUSES.get(timer['type'])
            if status is None:
                continue

            profile = BackupProfileModel.get_or_none(id=profile_id)
            if profile is None:
                continue

            repo_url = profile.repo.url if profile.repo else None
            pending.append(PendingJob(profile_id, profile.name, repo_url, timer['dt'], status))

        return sorted(pending, key=lambda job: job.scheduled_at)

    def mark_paused(self, profile: BackupProfileModel, until: dt) -> None:
        """Report the pause as the schedule status, unless the profile has no schedule to block."""
        if profile.repo is None or profile.schedule_mode == 'off':
            return

        self.timers[profile.id] = {'type': ScheduleStatusType.PAUSED, 'dt': until}
        self.scheduler.schedule_changed.emit()

    def remove_job(self, profile_id: int) -> None:
        if profile_id in self.timers:
            qtimer = self.timers[profile_id].get('qtt')
            if qtimer is not None:
                qtimer.stop()

            del self.timers[profile_id]
