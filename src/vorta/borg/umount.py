import os.path

import psutil

from vorta import config
from vorta.i18n import translate

from ..i18n import trans_late
from .borg_job import BorgJob


class BorgUmountJob(BorgJob):
    def started_event(self):
        self.updated.emit(self.tr('Unmounting archive…'))

    def finished_event(self, result):
        self.result.emit(result)
        if result['returncode'] != 0:
            self.app.backup_progress_event.emit(
                f"[{self.params['profile_name']}] "
                + translate(
                    'BorgMountJob', 'Umount command has failed. See the <a href="{0}">logs</a> for details.'
                ).format(config.LOG_DIR.as_uri())
            )

    @classmethod
    def prepare(cls, profile, mount_point, archive_name=None):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        archive_mount_points = []
        partitions = psutil.disk_partitions(all=True)
        for p in partitions:
            if p.device == 'borgfs':
                archive_mount_points.append(os.path.normpath(p.mountpoint))
        ret['active_mount_points'] = archive_mount_points

        if len(archive_mount_points) == 0:
            ret['message'] = trans_late('messages', 'No active Borg mounts found.')
            return ret
        if os.path.normpath(mount_point) not in archive_mount_points:
            ret['message'] = trans_late('messages', 'Mount point not active.')
            return ret

        if archive_name:
            ret['current_archive'] = archive_name
        ret['mount_point'] = mount_point

        cmd = ['borg', 'umount', '--log-json', mount_point]

        ret['ok'] = True
        ret['cmd'] = cmd

        return ret
