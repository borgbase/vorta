from .borg_thread import BorgThread


class BorgDiffThread(BorgThread):

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
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        cmd = ['borg', 'diff', '--info', '--log-json']
        cmd.append(f'{profile.repo.url}::{archive_name_1}')
        cmd.append(f'{archive_name_2}')

        ret['ok'] = True
        ret['cmd'] = cmd

        return ret

    def process_result(self, result):
        pass
