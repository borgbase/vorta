from .borg_thread import BorgThread


class BorgExtractThread(BorgThread):

    def log_event(self, msg):
        self.app.backup_log_event.emit(msg)

    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_log_event.emit('Downloading files from archive..')

    def finished_event(self, result):
        self.app.backup_finished_event.emit(result)
        self.result.emit(result)
        self.app.backup_log_event.emit('Restored files from archive.')

    @classmethod
    def prepare(cls, profile, archive_name, selected_files, destination_folder):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        cmd = ['borg', 'extract', '--list', '--info', '--log-json']
        cmd.append(f'{profile.repo.url}::{archive_name}')
        for s in selected_files:
            cmd.append(s)

        ret['ok'] = True
        ret['cmd'] = cmd
        ret['cwd'] = destination_folder

        return ret

    def process_result(self, result):
        pass
