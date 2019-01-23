import os
import tempfile
from dateutil import parser
import subprocess

from ..i18n import trans_late
from ..utils import get_current_wifi, format_archive_name
from ..models import SourceFileModel, ArchiveModel, WifiSettingModel, RepoModel
from .borg_thread import BorgThread


class BorgCreateThread(BorgThread):
    def process_result(self, result):
        if result['returncode'] in [0, 1] and 'archive' in result['data']:
            new_archive, created = ArchiveModel.get_or_create(
                snapshot_id=result['data']['archive']['id'],
                defaults={
                    'name': result['data']['archive']['name'],
                    'time': parser.parse(result['data']['archive']['start']),
                    'repo': result['params']['repo_id'],
                    'duration': result['data']['archive']['duration'],
                    'size': result['data']['archive']['stats']['deduplicated_size']
                }
            )
            new_archive.save()
            if 'cache' in result['data'] and created:
                stats = result['data']['cache']['stats']
                repo = RepoModel.get(id=result['params']['repo_id'])
                repo.total_size = stats['total_size']
                repo.unique_csize = stats['unique_csize']
                repo.unique_size = stats['unique_size']
                repo.total_unique_chunks = stats['total_unique_chunks']
                repo.save()

            self.app.backup_log_event.emit(self.tr('Backup finished.'))

    def log_event(self, msg):
        self.app.backup_log_event.emit(msg)

    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_log_event.emit(self.tr('Backup started.'))

    def finished_event(self, result):
        self.app.backup_finished_event.emit(result)
        self.pre_post_backup_cmd(self.params, cmd='post_backup_cmd', returncode=result['returncode'])

    @classmethod
    def pre_post_backup_cmd(cls, params, cmd='pre_backup_cmd', returncode=0):
        cmd = getattr(params['profile'], cmd)
        if cmd:
            env = {
                **os.environ.copy(),
                'repo_url': params['repo'].url,
                'profile_name': params['profile'].name,
                'profile_slug': params['profile'].slug(),
                'returncode': str(returncode)
            }
            proc = subprocess.run(cmd, shell=True, env=env)
            return proc.returncode
        else:
            return 0  # 0 if no command was run.

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
            ret['ok'] = False  # Set back to False, so we can do our own checks here.

        n_backup_folders = SourceFileModel.select().count()
        if n_backup_folders == 0:
            ret['message'] = trans_late('messages', 'Add some folders to back up first.')
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
                ret['message'] = trans_late('messages', 'Current Wifi is not allowed.')
                return ret

        if not profile.repo.is_remote_repo() and not os.path.exists(profile.repo.url):
            ret['message'] = trans_late('messages', 'Repo folder not mounted or moved.')
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
        new_archive_name = format_archive_name(profile, profile.new_archive_name)
        cmd.append(f"{profile.repo.url}::{new_archive_name}")

        for f in SourceFileModel.select().where(SourceFileModel.profile == profile.id):
            cmd.append(f.dir)

        # Run user-supplied pre-backup command
        ret['profile'] = profile
        ret['repo'] = profile.repo
        if cls.pre_post_backup_cmd(ret) != 0:
            ret['message'] = trans_late('messages', 'Pre-backup command returned non-zero exit code.')
            return ret

        ret['message'] = trans_late('messages', 'Starting backup...')
        ret['ok'] = True
        ret['cmd'] = cmd

        return ret
