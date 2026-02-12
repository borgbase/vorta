from typing import Any, Dict

from vorta.borg._compatibility import MIN_BORG_FOR_FEATURE
from vorta.i18n import trans_late
from vorta.utils import borg_compat

from .borg_job import BorgJob


class BorgKeyImportJob(BorgJob):
    """Import repository key from backup."""

    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {self.tr('Importing repository key…')}")

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

        if result['returncode'] == 0:
            self.app.backup_progress_event.emit(
                f"[{self.params['profile_name']}] {self.tr('Repository key imported successfully.')}"
            )
        else:
            self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {self.tr('Key import failed.')}")

    @classmethod
    def prepare(cls, profile, input_path):
        """
        Prepare key import command.

        Parameters
        ----------
        profile : BackupProfileModel
            The profile with repository to import key into
        input_path : str
            Path to the backup key file to import

        Note: --paper flag is intentionally not supported as it requires
        interactive input which is not suitable for GUI operation.
        """
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        if not borg_compat.check('KEY_IMPORT'):
            ret['message'] = trans_late(
                'messages',
                'This feature needs Borg {} or higher.'.format(MIN_BORG_FOR_FEATURE['KEY_IMPORT']),
            )
            return ret

        cmd = ['borg', 'key', 'import', '--info', '--log-json']

        # Handle v1 vs v2 syntax for repository argument
        if borg_compat.check('V2'):
            cmd.extend(['--repo', profile.repo.url])
        else:
            cmd.append(profile.repo.url)

        # Add input path
        cmd.append(input_path)

        ret['ok'] = True
        ret['cmd'] = cmd

        return ret
