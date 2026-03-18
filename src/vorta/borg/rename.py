from __future__ import annotations

from typing import Any

from vorta.store.models import ArchiveModel, RepoModel
from vorta.utils import borg_compat

from .borg_job import BorgJob


class BorgRenameJob(BorgJob):
    def started_event(self) -> None:
        self.app.backup_started_event.emit()
        self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {self.tr('Renaming archive…')}")

    def log_event(self, msg: str) -> None:
        self.app.backup_log_event.emit(msg)

    @classmethod
    def prepare(cls, profile: Any, old_archive_name: str, new_archive_name: str) -> dict[str, Any]:
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        cmd = ['borg', 'rename', '--info', '--log-json']
        if borg_compat.check('V2'):
            cmd.extend(["-r", profile.repo.url, old_archive_name, new_archive_name])
        else:
            cmd.extend([f'{profile.repo.url}::{old_archive_name}', new_archive_name])

        ret['old_archive_name'] = old_archive_name
        ret['new_archive_name'] = new_archive_name
        ret['repo_url'] = profile.repo.url
        ret['ok'] = True
        ret['cmd'] = cmd

        return ret

    def process_result(self, result: dict[str, Any]) -> None:
        if result['returncode'] == 0:
            repo = RepoModel.get(url=result['params']['repo_url'])
            renamed_archive = ArchiveModel.get(name=result['params']['old_archive_name'], repo=repo)
            renamed_archive.name = result['params']['new_archive_name']
            renamed_archive.save()

            self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {self.tr('Archive renamed.')}")
