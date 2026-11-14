from vorta.utils import borg_compat

from .borg_job import BorgJob


class BorgDiffJob(BorgJob):
    emits_backup_finished = True

    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_progress_event.emit(
            f"[{self.params['profile_name']}] {self.tr('Requesting differences between archives…')}"
        )

    def finished_event(self, result):
        self._emit_backup_finished(result)
        self.app.backup_progress_event.emit(
            f"[{self.params['profile_name']}] {self.tr('Obtained differences between archives.')}"
        )
        self._emit_result(result)

    @classmethod
    def prepare(cls, profile, archive_name_1, archive_name_2):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret

        ret['cmd'] = ['borg', 'diff', '--info', '--log-json']
        ret['json_lines'] = False
        if borg_compat.check('DIFF_JSON_LINES'):
            ret['cmd'].append('--json-lines')
            ret['json_lines'] = True

        if borg_compat.check('V2'):
            ret['cmd'].extend(['-r', profile.repo.url, archive_name_1, archive_name_2])
        else:
            ret['cmd'].extend([f'{profile.repo.url}::{archive_name_1}', archive_name_2])

        ret['ok'] = True
        ret['archive_name_older'] = archive_name_1
        ret['archive_name_newer'] = archive_name_2

        return ret
