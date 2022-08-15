from typing import Any, Dict
from vorta.i18n import trans_late
from vorta.utils import borg_compat
from .borg_job import BorgJob


class BorgCompactJob(BorgJob):
    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_progress_event.emit(self.tr('Starting repository compaction...'))

    def finished_event(self, result: Dict[str, Any]):
        """
        Process that the job terminated with the given results.

        Parameters
        ----------
        result : Dict[str, Any]
            The (json-like) dictionary containing the job results.
        """
        self.app.backup_finished_event.emit(result)
        self.result.emit(result)
        if result['returncode'] != 0:
            self.app.backup_progress_event.emit(self.tr('Errors during compaction. See logs for details.'))
        else:
            self.app.backup_progress_event.emit(self.tr('Compaction completed.'))

    @classmethod
    def prepare(cls, profile):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        if not borg_compat.check('COMPACT_SUBCOMMAND'):
            ret['ok'] = False
            ret['message'] = trans_late('messages', 'This feature needs Borg 1.2.0 or higher.')
            return ret

        cmd = ['borg', '--info', '--log-json', 'compact', '--cleanup-commits']
        cmd.append(f'{profile.repo.url}')

        ret['ok'] = True
        ret['cmd'] = cmd

        return ret
