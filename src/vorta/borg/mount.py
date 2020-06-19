import os
from .borg_thread import BorgThread


class BorgMountThread(BorgThread):

    def started_event(self):
        self.updated.emit(self.tr('Mounting archive into folder...'))

    @classmethod
    def prepare(cls, profile, overrideMountOpts):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        cmd = ['borg', '--log-json', 'mount', '-o', f"umask=0277,uid={os.getuid()}", f"{profile.repo.url}"]

        if not overrideMountOpts:
            del cmd[3:5]

        ret['ok'] = True
        ret['cmd'] = cmd

        return ret
