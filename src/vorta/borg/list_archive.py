import json

from vorta.utils import borg_compat
from vorta.views.dialogs.archive.extract import ExtractTree, parse_json_lines

from .borg_job import BorgJob, LineBuffer


class BorgListArchiveJob(BorgJob):
    emits_backup_finished = True

    def run(self):
        # SiteWorker calls run() on its worker thread, unlike __init__().
        self.model = ExtractTree()
        self.line_buffer = LineBuffer()
        super().run()

    def process_intermediate(self, stdout_data: str, more: bool):
        lines = self.line_buffer.process(stdout_data)
        if not more:
            lines.extend(self.line_buffer.flush())
        if lines:
            parse_json_lines([json.loads(line) for line in lines], self.model)

    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {self.tr('Getting archive content…')}")

    def finished_event(self, result):
        # The model was created and populated in run()'s worker thread. The job
        # was created on the consumer's thread, so transfer the model there
        # before emitting the result; callers must keep that assumption true.
        self.model.moveToThread(self.thread())
        result['ret'] = self.model
        self._emit_backup_finished(result)
        self.app.backup_progress_event.emit(
            f"[{self.params['profile_name']}] {self.tr('Done getting archive content.')}"
        )
        self._emit_result(result)

    @classmethod
    def prepare(cls, profile, archive_name):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret

        ret['archive_name'] = archive_name
        ret['cmd'] = [
            'borg',
            'list',
            '--info',
            '--log-json',
            '--json-lines',
            '--format',
            # fields to include in json output
            "{mode}{user}{group}{size}{"
            + ('isomtime' if borg_compat.check('V122') else 'mtime')
            + "}{path}{source}{health}{NL}",
        ]

        ret['cmd'] += borg_compat.repo_args(profile.repo.url, archive_name)

        ret['ok'] = True

        return ret
