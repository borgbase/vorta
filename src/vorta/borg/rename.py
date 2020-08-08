from .borg_thread import BorgThread


class BorgRenameThread(BorgThread):

    def log_event(self, msg):
        self.app.backup_log_event.emit(msg)

    @classmethod
    def prepare(cls, profile):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        cmd = ['borg', 'rename', '--info', '--log-json']
        cmd.append(f'{profile.repo.url}')

        ret['ok'] = True
        ret['cmd'] = cmd

        return ret
