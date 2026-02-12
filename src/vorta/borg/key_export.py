from typing import Any, Dict

from vorta.borg._compatibility import MIN_BORG_FOR_FEATURE
from vorta.i18n import trans_late
from vorta.utils import borg_compat

from .borg_job import BorgJob


class BorgKeyExportJob(BorgJob):
    """Export repository key for backup."""

    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {self.tr('Exporting repository key…')}")

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
                f"[{self.params['profile_name']}] {self.tr('Repository key exported successfully.')}"
            )
        else:
            self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {self.tr('Key export failed.')}")

    @classmethod
    def prepare(cls, profile, output_path, paper=False, qr_html=False):
        """
        Prepare key export command.

        Parameters
        ----------
        profile : BackupProfileModel
            The profile with repository to export key from
        output_path : str
            Path where to save the exported key
        paper : bool
            Create an export suitable for printing and later type-in
        qr_html : bool
            Create an html file suitable for printing and later type-in or qr scan
        """
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        if not borg_compat.check('KEY_EXPORT'):
            ret['message'] = trans_late(
                'messages',
                'This feature needs Borg {} or higher.'.format(MIN_BORG_FOR_FEATURE['KEY_EXPORT']),
            )
            return ret

        cmd = ['borg', 'key', 'export', '--info', '--log-json']

        # Add optional flags (mutually exclusive)
        if qr_html:
            cmd.append('--qr-html')
        elif paper:
            cmd.append('--paper')

        # Handle v1 vs v2 syntax for repository argument
        if borg_compat.check('V2'):
            cmd.extend(['--repo', profile.repo.url])
        else:
            cmd.append(profile.repo.url)

        # Add output path
        cmd.append(output_path)

        ret['ok'] = True
        ret['cmd'] = cmd

        return ret
