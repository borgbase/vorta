from collections import namedtuple

import psutil

import vorta.borg.umount
from vorta.borg.borg_job import BorgJob
from vorta.borg.umount import BorgUmountJob


def test_umount_matches_symlinked_mount_point(monkeypatch):
    """psutil canonicalizes paths (e.g. /home -> /var/home on Silverblue).

    The user-facing mount path stored by Vorta may include a symlink, so
    comparison must use realpath on both sides (#1461).
    """
    user_facing = '/home/test/.mnt/archive'
    canonical = '/var/home/test/.mnt/archive'

    DiskPartitions = namedtuple('DiskPartitions', ['device', 'mountpoint'])

    def fake_disk_partitions(**kwargs):
        return [DiskPartitions('borgfs', canonical)]

    def fake_realpath(p, *args, **kwargs):
        if p == user_facing:
            return canonical
        return p

    monkeypatch.setattr(psutil, 'disk_partitions', fake_disk_partitions)
    monkeypatch.setattr(vorta.borg.umount.os.path, 'realpath', fake_realpath)
    monkeypatch.setattr(BorgJob, 'prepare', classmethod(lambda cls, profile: {'ok': True}))

    ret = BorgUmountJob.prepare(profile=None, mount_point=user_facing)

    assert ret['ok'] is True
    assert ret['mount_point'] == user_facing
    assert canonical in ret['active_mount_points']
