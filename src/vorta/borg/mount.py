from os import getuid
from .borg_thread import BorgThread
from vorta.models import SettingsModel


class BorgMountThread(BorgThread):

    def started_event(self):
        self.updated.emit(self.tr('Mounting archive into folder...'))

    @classmethod
    def prepare(cls, profile):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        cmd = ['borg', '--log-json', 'mount']

        override_mount_permissions = SettingsModel.get(key='override_mount_permissions').value
        if override_mount_permissions:
            cmd += ['-o', f"umask=0277,uid={getuid()}"]

        cmd += [f"{profile.repo.url}"]

        ret['ok'] = True
        ret['cmd'] = cmd

        return ret
