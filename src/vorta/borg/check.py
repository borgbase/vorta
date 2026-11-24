from typing import Any, Dict

from vorta import config
from vorta.i18n import translate
from vorta.i18n.richtext import escape, format_richtext, link
from vorta.utils import borg_compat

from .borg_job import BorgJob


class BorgCheckJob(BorgJob):
    emits_backup_finished = True
    should_inhibit = True

    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {self.tr('Starting consistency check…')}")

    def finished_event(self, result: Dict[str, Any]):
        """
        Process that the job terminated with the given results.

        Parameters
        ----------
        result : Dict[str, Any]
            The (json-like) dictionary containing the job results.
        """
        self._emit_backup_finished(result)
        self._emit_result(result)
        if result['returncode'] != 0:
            logs_link = link(config.LOG_DIR.as_uri(), translate('messages', 'logs'))
            message = format_richtext(
                escape(translate('RepoCheckJob', 'Repo check failed. See the %1 for details.')),
                logs_link,
            )
            self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] " + message)
            self.app.check_failed_event.emit(result)
        else:
            self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {self.tr('Check completed.')}")

    @classmethod
    def prepare(cls, profile, archive=None):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        cmd = ['borg', 'check', '--info', '--log-json', '--progress']
        cmd += borg_compat.repo_args(profile.repo.url, archive or None, match=True)

        ret['ok'] = True
        ret['cmd'] = cmd

        return ret
