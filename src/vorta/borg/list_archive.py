from .borg_job import BorgJob


class BorgListArchiveJob(BorgJob):

    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_progress_event.emit(self.tr('Getting archive content...'))

    def finished_event(self, result):
        self.app.backup_finished_event.emit(result)
        self.app.backup_progress_event.emit(self.tr('Done getting archive content.'))
        self.result.emit(result)

    @classmethod
    def prepare(cls, profile, archive_name):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret

        ret['archive_name'] = archive_name
        ret['cmd'] = [
            'borg', 'list', '--info', '--log-json', '--json-lines',
            '--format', "{size:8d}{TAB}{mtime}{TAB}{path}{NL}",
            f'{profile.repo.url}::{archive_name}']
        ret['ok'] = True

        return ret
