from .borg_thread import BorgThread


class BorgCheckThread(BorgThread):

    def log_event(self, msg):
        self.app.backup_log_event.emit(msg)

    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_log_event.emit(self.tr('Starting consistency check...'))

    def finished_event(self, result):
        self.app.backup_finished_event.emit(result)
        self.result.emit(result)

    @classmethod
    def prepare(cls, profile):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        cmd = ['borg', 'check', '--info', '--log-json']
        cmd.append(f'{profile.repo.url}')

        ret['ok'] = True
        ret['cmd'] = cmd

        return ret
