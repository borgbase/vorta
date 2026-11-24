from vorta import config
from vorta.i18n import translate
from vorta.i18n.richtext import escape, format_richtext, link
from vorta.utils import borg_compat

from .borg_job import BorgJob


class BorgBreakJob(BorgJob):
    emits_backup_finished = True

    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {self.tr('Breaking repository lock…')}")

    def finished_event(self, result):
        self._emit_backup_finished(result)
        if result['returncode'] == 0:
            message = self.tr('Repository lock broken. Please redo your last action.')
        else:
            logs_link = link(config.LOG_DIR.as_uri(), translate('messages', 'logs'))
            message = format_richtext(
                escape(translate('BorgBreakJob', 'Breaking the repository lock failed. See the %1 for details.')),
                logs_link,
            )
        self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {message}")
        self._emit_result(result)

    @classmethod
    def prepare(cls, profile):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        cmd = ['borg', 'break-lock', '--info', '--log-json']
        cmd += borg_compat.repo_args(profile.repo.url)

        ret['ok'] = True
        ret['cmd'] = cmd

        return ret
