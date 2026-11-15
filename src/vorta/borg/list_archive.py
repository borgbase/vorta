import json

from PyQt6 import QtCore

from vorta.utils import borg_compat

from .borg_job import BorgJob


class BorgListArchiveJob(BorgJob):
    emits_backup_finished = True

    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {self.tr('Getting archive content…')}")

    def finished_event(self, result):
        self._emit_backup_finished(result)
        self.app.backup_progress_event.emit(
            f"[{self.params['profile_name']}] {self.tr('Done getting archive content.')}"
        )
        self._emit_result(result)

    @classmethod
    def prepare(cls, profile, archive_name):
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

        ret['cmd'] += borg_compat.repo_args(profile.repo.url, archive_name)

        ret['ok'] = True

        return ret
