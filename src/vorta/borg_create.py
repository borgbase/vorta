import os
import tempfile
import platform
from dateutil import parser
from datetime import datetime as dt

from .models import SourceDirModel, BackupProfileModel, WifiSettingModel, SnapshotModel, BackupProfileMixin
from .utils import get_current_wifi, keyring
from .borg_thread import BorgThread


class BorgCreateThread(BorgThread, BackupProfileMixin):
    def process_result(self, result):
        if result['returncode'] == 0:
            new_snapshot, created = SnapshotModel.get_or_create(
                snapshot_id=result['data']['archive']['id'],
                defaults={
                    'name': result['data']['archive']['name'],
                    'time': parser.parse(result['data']['archive']['start']),
                    'repo': self.profile.repo,
                    'duration': result['data']['archive']['duration'],
                    'size': result['data']['archive']['stats']['deduplicated_size']
                }
            )
            new_snapshot.save()
            if 'cache' in result['data'] and created:
                stats = result['data']['cache']['stats']
                repo = self.profile.repo
                repo.total_size = stats['total_size']
                repo.unique_csize = stats['unique_csize']
                repo.unique_size = stats['unique_size']
                repo.total_unique_chunks = stats['total_unique_chunks']
                repo.save()

    def log_event(self, msg):
        self.app.backup_log_event.emit(msg)

    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_log_event.emit('Backup started.')

    def finished_event(self, result):
        self.app.backup_finished_event.emit(result)

    @classmethod
    def prepare(cls):
        """
        `borg create` is called from different places and needs some preparation.
        Centralize it here and return the required arguments to the caller.
        """
        profile = BackupProfileModel.get(id=1)

        ret = {'ok': False}

        if cls.is_running():
            ret['message'] = 'Backup is already in progress.'
            return ret

        if profile.repo is None:
            ret['message'] = 'Add a remote backup repository first.'
            return ret

        n_backup_folders = SourceDirModel.select().count()
        if n_backup_folders == 0:
            ret['message'] = 'Add some folders to back up first.'
            return ret

        current_wifi = get_current_wifi()
        if current_wifi is not None:
            wifi_is_disallowed = WifiSettingModel.select().where(
                (WifiSettingModel.ssid == current_wifi)
                & (WifiSettingModel.allowed == False)
                & (WifiSettingModel.profile == profile.id)
            )
            if wifi_is_disallowed.count() > 0:
                ret['message'] = 'Current Wifi is not allowed.'
                return ret

        params = {'password': keyring.get_password("vorta-repo", profile.repo.url)}
        cmd = ['borg', 'create', '--list', '--info', '--log-json', '--json', '-C', profile.compression]

        # Add excludes
        # Partly inspired by borgmatic/borgmatic/borg/create.py
        if profile.exclude_patterns is not None:
            exclude_dirs = []
            for p in profile.exclude_patterns.split('\n'):
                if p.strip():
                    expanded_directory = os.path.expanduser(p.strip())
                    exclude_dirs.append(expanded_directory)

            if exclude_dirs:
                pattern_file = tempfile.NamedTemporaryFile('w', delete=False)
                pattern_file.write('\n'.join(exclude_dirs))
                pattern_file.flush()
                cmd.extend(['--exclude-from', pattern_file.name])

        if profile.exclude_if_present is not None:
            for f in profile.exclude_if_present.split('\n'):
                if f.strip():
                    cmd.extend(['--exclude-if-present', f.strip()])

        # Add repo url and source dirs.
        cmd.append(f'{profile.repo.url}::{platform.node()}-{dt.now().isoformat()}')

        for f in SourceDirModel.select():
            cmd.append(f.dir)

        ret['message'] = 'Starting backup..'
        ret['ok'] = True
        ret['cmd'] = cmd
        ret['params'] = params

        return ret
