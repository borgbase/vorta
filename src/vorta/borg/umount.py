import psutil
from .borg_thread import BorgThread


class BorgUmountThread(BorgThread):

    def started_event(self):
        self.updated.emit('Unmounting archive...')

    @classmethod
    def prepare(cls, profile):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        ret['active_mount_points'] = []
        partitions = psutil.disk_partitions(all=True)
        for p in partitions:
            if p.device == 'borgfs':
                ret['active_mount_points'].append(p.mountpoint)

        if len(ret['active_mount_points']) == 0:
            ret['message'] = 'No active Borg mounts found.'
            return ret

        cmd = ['borg', 'umount', '--log-json']

        ret['ok'] = True
        ret['cmd'] = cmd

        return ret
