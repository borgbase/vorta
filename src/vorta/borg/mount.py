from os import getuid
from .borg_thread import BorgThread


class BorgMountThread(BorgThread):

    def started_event(self):
        self.updated.emit(self.tr('Mounting archive into folder...'))

    @classmethod
    def prepare(cls, profile, override_mount_opts):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        cmd = ['borg', '--log-json', 'mount', f"{profile.repo.url}"]

        if override_mount_opts:
            cmd[3:3] = ['-o', f"umask=0277,uid={getuid()}"]

        ret['ok'] = True
        ret['cmd'] = cmd

        return ret
