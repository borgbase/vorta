from typing import Any, Dict
from vorta.config import LOG_DIR
from vorta.i18n import trans_late, translate
from vorta.utils import borg_compat
from .borg_job import BorgJob


class BorgChangePassJob(BorgJob):
    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_progress_event.emit(self.tr('Changing Borg passphrase...'))

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
            self.app.backup_progress_event.emit(
                translate(
                    'BorgChangePassJob',
                    'Errors during changing passphrase. See the <a href="{0}">logs</a> for details.',
                ).format(LOG_DIR.as_uri())
            )
        else:
            self.app.backup_progress_event.emit(self.tr('Borg passphrase changed.'))

    @classmethod
    def prepare(cls, profile, oldPass, newPass):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        if not borg_compat.check('CHANGE_PASSPHRASE'):
            ret['ok'] = False
            ret['message'] = trans_late('messages', 'This feature needs Borg 1.1.0 or higher.')
            return ret

        cmd = ['borg', '--info', '--log-json', 'key', 'change-passphrase']
        cmd.append(f'{profile.repo.url}')

        ret['password'] = oldPass
        ret['additional_env'] = {'BORG_NEW_PASSPHRASE': newPass}

        ret['ok'] = True
        ret['cmd'] = cmd

        return ret
