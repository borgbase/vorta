import os
import tempfile
import platform
from dateutil import parser
from datetime import datetime as dt

from ..utils import get_current_wifi
from ..models import SourceFileModel, ArchiveModel, WifiSettingModel, RepoModel
from .borg_thread import BorgThread


class BorgCreateThread(BorgThread):
    def process_result(self, result):
        if result['returncode'] in [0, 1] and 'archive' in result['data']:
            new_snapshot, created = ArchiveModel.get_or_create(
                snapshot_id=result['data']['archive']['id'],
                defaults={
                    'name': result['data']['archive']['name'],
                    'time': parser.parse(result['data']['archive']['start']),
                    'repo': result['params']['repo_id'],
                    'duration': result['data']['archive']['duration'],
                    'size': result['data']['archive']['stats']['deduplicated_size']
                }
            )
            new_snapshot.save()
            if 'cache' in result['data'] and created:
                stats = result['data']['cache']['stats']
                repo = RepoModel.get(id=result['params']['repo_id'])
                repo.total_size = stats['total_size']
                repo.unique_csize = stats['unique_csize']
                repo.unique_size = stats['unique_size']
                repo.total_unique_chunks = stats['total_unique_chunks']
                repo.save()

            self.app.backup_log_event.emit('Backup finished.')

    def log_event(self, msg):
        self.app.backup_log_event.emit(msg)

    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_log_event.emit('Backup started.')

    def finished_event(self, result):
        self.app.backup_finished_event.emit(result)

    @classmethod
    def prepare(cls, profile):
        """
        `borg create` is called from different places and needs some preparation.
        Centralize it here and return the required arguments to the caller.
        """
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        n_backup_folders = SourceFileModel.select().count()
        if n_backup_folders == 0:
            ret['message'] = 'Add some folders to back up first.'
            return ret

        current_wifi = get_current_wifi()
        if current_wifi is not None:
            wifi_is_disallowed = WifiSettingModel.select().where(
                (
                    WifiSettingModel.ssid == current_wifi
                ) & (
                    WifiSettingModel.allowed == False  # noqa
                ) & (
                    WifiSettingModel.profile == profile
                )
            )
            if wifi_is_disallowed.count() > 0 and profile.repo.is_remote_repo():
                ret['message'] = 'Current Wifi is not allowed.'
                return ret

        if not profile.repo.is_remote_repo() and not os.path.exists(profile.repo.url):
            ret['message'] = 'Repo folder not mounted or moved.'
            return ret

        cmd = ['borg', 'create', '--list', '--info', '--log-json', '--json', '--filter=AM', '-C', profile.compression]

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
        cmd.append(f"{profile.repo.url}::{platform.node()}-{profile.slug()}-{dt.now().isoformat(timespec='seconds')}")

        for f in SourceFileModel.select().where(SourceFileModel.profile == profile.id):
            cmd.append(f.dir)

        ret['message'] = 'Starting backup..'
        ret['ok'] = True
        ret['cmd'] = cmd

        return ret
