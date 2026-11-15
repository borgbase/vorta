import re
from typing import List

from vorta.store.models import RepoModel
from vorta.utils import borg_compat

from .borg_job import BorgJob


class BorgDeleteJob(BorgJob):
    emits_backup_finished = True

    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {self.tr('Deleting archive…')}")

    def finished_event(self, result):
        # set repo stats to N/A
        repo = RepoModel.get(id=result['params']['repo_id'])
        repo.total_size = None
        repo.unique_csize = None
        repo.unique_size = None
        repo.total_unique_chunks = None
        repo.save()

        self._emit_backup_finished(result)
        self._emit_result(result)
        self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {self.tr('Archive deleted.')}")

    @classmethod
    def prepare(cls, profile, archives: List[str]):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        if len(archives) <= 0:
            return ret

        cmd = ['borg', 'delete', '--info', '--log-json']
        if borg_compat.check('V2'):
            cmd += borg_compat.repo_args(profile.repo.url)
            cmd += ['-a', 're:(?:' + '|'.join(map(re.escape, archives)) + ')']
        else:
            cmd += borg_compat.repo_args(profile.repo.url, archives[0]) + archives[1:]

        ret['archives'] = archives
        ret['cmd'] = cmd
        ret['ok'] = True

        return ret
