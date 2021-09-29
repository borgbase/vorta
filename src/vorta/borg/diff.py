from .borg_job import BorgJob
from vorta.utils import borg_compat


class BorgDiffJob(BorgJob):

    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_progress_event.emit(self.tr('Requesting differences between archives...'))

    def finished_event(self, result):
        self.app.backup_finished_event.emit(result)
        self.app.backup_progress_event.emit(self.tr('Obtained differences between archives.'))
        self.result.emit(result)

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

        ret['cmd'].extend([
            f'{profile.repo.url}::{archive_name_1}',
            f'{archive_name_2}'
        ])
        ret['ok'] = True
        ret['archive_name_older'] = archive_name_1
        ret['archive_name_newer'] = archive_name_2

        return ret
