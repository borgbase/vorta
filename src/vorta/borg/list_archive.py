from __future__ import annotations

from typing import Any

from vorta.utils import borg_compat

from vorta.store.models import BackupProfileModel

from .borg_job import BorgJob


class BorgListArchiveJob(BorgJob):
    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {self.tr('Getting archive content…')}")

    def finished_event(self, result: dict[str, Any]):
        self.app.backup_finished_event.emit(result)
        self.app.backup_progress_event.emit(
            f"[{self.params['profile_name']}] {self.tr('Done getting archive content.')}"
        )
        self.result.emit(result)

    @classmethod
    def prepare(cls, profile: BackupProfileModel, archive_name: str) -> dict[str, Any]:
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret

        ret['archive_name'] = archive_name
        ret['cmd'] = [
            'borg',
            'list',
            '--info',
            '--log-json',
            '--json-lines',
            '--format',
            # fields to include in json output
            "{mode}{user}{group}{size}{"
            + ('isomtime' if borg_compat.check('V122') else 'mtime')
            + "}{path}{source}{health}{NL}",
        ]

        if borg_compat.check('V2'):
            ret['cmd'].extend(["-r", profile.repo.url, archive_name])
        else:
            ret['cmd'].append(f'{profile.repo.url}::{archive_name}')

        ret['ok'] = True

        return ret
