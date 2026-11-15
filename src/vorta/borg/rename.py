from vorta.store.models import ArchiveModel, RepoModel
from vorta.utils import borg_compat

from .borg_job import BorgJob


class BorgRenameJob(BorgJob):
    emits_backup_finished = True

    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {self.tr('Renaming archive…')}")

    def finished_event(self, result):
        self._emit_backup_finished(result)
        self._emit_result(result)

    def log_event(self, msg):
        self.app.backup_log_event.emit(msg)

    @classmethod
    def prepare(cls, profile, old_archive_name, new_archive_name):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        cmd = ['borg', 'rename', '--info', '--log-json']
        cmd += borg_compat.repo_args(profile.repo.url, old_archive_name) + [new_archive_name]

        ret['old_archive_name'] = old_archive_name
        ret['new_archive_name'] = new_archive_name
        ret['repo_url'] = profile.repo.url
        ret['ok'] = True
        ret['cmd'] = cmd

        return ret

    def process_result(self, result):
        if result['returncode'] == 0:
            repo = RepoModel.get(url=result['params']['repo_url'])
            renamed_archive = ArchiveModel.get(name=result['params']['old_archive_name'], repo=repo)
            renamed_archive.name = result['params']['new_archive_name']
            renamed_archive.save()

            self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {self.tr('Archive renamed.')}")
