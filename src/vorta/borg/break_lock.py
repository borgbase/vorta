from __future__ import annotations

from typing import Any

from .borg_job import BorgJob


class BorgBreakJob(BorgJob):
    def started_event(self) -> None:
        self.app.backup_started_event.emit()
        self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {self.tr('Breaking repository lock…')}")

    def finished_event(self, result: dict[str, Any]) -> None:
        self.app.backup_finished_event.emit(result)
        self.app.backup_progress_event.emit(
            f"[{self.params['profile_name']}] {self.tr('Repository lock broken. Please redo your last action.')}"
        )
        self.result.emit(result)

    @classmethod
    def prepare(cls, profile: Any) -> dict[str, Any]:
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        cmd = ['borg', 'break-lock', '--info', '--log-json']
        cmd.append(f'{profile.repo.url}')

        ret['ok'] = True
        ret['cmd'] = cmd

        return ret
