from .borg_thread import BorgThread


class BorgListArchiveThread(BorgThread):

    def log_event(self, msg):
        self.app.backup_log_event.emit(msg)

    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_log_event.emit(self.tr('Getting archive content...'))

    def finished_event(self, result):
        self.app.backup_finished_event.emit(result)
        self.app.backup_log_event.emit(self.tr('Done getting archive content.'))
        self.result.emit(result)

    @classmethod
    def prepare(cls, profile):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        cmd = ['borg', 'list', '--info', '--log-json', '--format', "{size:8d}{TAB}{mtime}{TAB}{path}{NL}"]
        cmd.append(f'{profile.repo.url}')

        ret['ok'] = True
        ret['cmd'] = cmd

        return ret
