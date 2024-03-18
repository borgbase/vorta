import os
import subprocess
import tempfile
from datetime import datetime as dt

from vorta import config
from vorta.i18n import trans_late, translate
from vorta.store.models import (
    ArchiveModel,
    RepoModel,
    SourceFileModel,
    WifiSettingModel,
)
from vorta.utils import borg_compat, format_archive_name, get_network_status_monitor

from .borg_job import BorgJob


class BorgCreateJob(BorgJob):
    def process_result(self, result):
        if result['returncode'] in [0, 1] and 'archive' in result['data']:
            new_archive, created = ArchiveModel.get_or_create(
                snapshot_id=result['data']['archive']['id'],
                defaults={
                    'name': result['data']['archive']['name'],
                    # SQLite can't save timezone, so we remove it here. TODO: Keep as UTC?
                    'time': dt.fromisoformat(result['data']['archive']['start']).replace(tzinfo=None),
                    'repo': result['params']['repo_id'],
                    'duration': result['data']['archive']['duration'],
                    'size': result['data']['archive']['stats']['deduplicated_size'],
                    'trigger': result['params'].get('category', 'user'),
                },
            )
            new_archive.save()
            if 'cache' in result['data'] and created:
                stats = result['data']['cache']['stats']
                repo = RepoModel.get(id=result['params']['repo_id'])
                repo.total_size = stats['total_size']
                # repo.unique_csize = stats['unique_csize']
                repo.unique_size = stats['unique_size']
                repo.total_unique_chunks = stats['total_unique_chunks']
                repo.save()

            if result['returncode'] == 1:
                self.app.backup_progress_event.emit(
                    f"[{self.params['profile_name']}] "
                    + translate(
                        'BorgCreateJob',
                        'Backup finished with warnings. See the <a href="{0}">logs</a> for details.',
                    ).format(config.LOG_DIR.as_uri())
                )
            else:
                self.app.backup_log_event.emit('', {})
                self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {self.tr('Backup finished.')}")

    def progress_event(self, fmt):
        self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {fmt}")

    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {self.tr('Backup started.')}")

    def finished_event(self, result):
        self.app.backup_finished_event.emit(result)
        self.result.emit(result)
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
                'returncode': str(returncode),
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

        n_backup_folders = SourceFileModel.select().where(SourceFileModel.profile == profile).count()

        # cmd options like `--paths-from-command` require a command
        # that is appended to the arguments
        # $ borg create --paths-from-command repo::archive1 -- find /home/user -type f -size -76M
        extra_cmd_options = []
        suffix_command = []
        if profile.repo.create_backup_cmd:
            s1, sep, s2 = profile.repo.create_backup_cmd.partition('-- ')
            extra_cmd_options = s1.split()
            suffix_command = (sep + s2).split()

        if n_backup_folders == 0 and '--paths-from-command' not in extra_cmd_options:
            ret['message'] = trans_late('messages', 'Add some folders to back up first.')
            return ret

        network_status_monitor = get_network_status_monitor()
        current_wifi = network_status_monitor.get_current_wifi()
        if current_wifi is not None:
            wifi_is_disallowed = WifiSettingModel.select().where(
                (WifiSettingModel.ssid == current_wifi)
                & (WifiSettingModel.allowed == False)  # noqa
                & (WifiSettingModel.profile == profile)
            )
            if wifi_is_disallowed.count() > 0 and profile.repo.is_remote_repo():
                ret['message'] = trans_late('messages', 'Current Wifi is not allowed.')
                return ret

        if (
            profile.repo.is_remote_repo()
            and profile.dont_run_on_metered_networks
            and network_status_monitor.is_network_metered()
        ):
            ret['message'] = trans_late('messages', 'Not running backup over metered connection.')
            return ret

        ret['profile'] = profile
        ret['repo'] = profile.repo

        # Run user-supplied pre-backup command
        if cls.pre_post_backup_cmd(ret) != 0:
            ret['message'] = trans_late('messages', 'Pre-backup command returned non-zero exit code.')
            return ret

        if not profile.repo.is_remote_repo() and not os.path.exists(profile.repo.url):
            ret['message'] = trans_late('messages', 'Repo folder not mounted or moved.')
            return ret

        if 'zstd' in profile.compression and not borg_compat.check('ZSTD'):
            ret['message'] = trans_late(
                'messages',
                'Your current Borg version does not support ZStd compression.',
            )
            return ret

        cmd = [
            'borg',
            'create',
            '--list',
            '--progress',
            '--info',
            '--log-json',
            '--json',
            '--filter=AM',
            '-C',
            profile.compression,
        ]
        cmd += extra_cmd_options

        # Add excludes
        # Partly inspired by borgmatic/borgmatic/borg/create.py
        exclude_dirs = []
        for p in profile.get_combined_exclusion_string().split('\n'):
            if p.strip():
                expanded_directory = os.path.expanduser(p.strip())
                exclude_dirs.append(expanded_directory)

        if exclude_dirs:
            pattern_file = tempfile.NamedTemporaryFile('w', delete=True)
            pattern_file.write('\n'.join(exclude_dirs))
            pattern_file.flush()
            cmd.extend(['--exclude-from', pattern_file.name])
            ret['cleanup_files'].append(pattern_file)

        # Currently not in use, but may be added back to the UI later.
        # if profile.exclude_if_present is not None:
        #     for f in profile.exclude_if_present.split('\n'):
        #         if f.strip():
        #             cmd.extend(['--exclude-if-present', f.strip()])

        # Add repo url and source dirs.
        new_archive_name = format_archive_name(profile, profile.new_archive_name)

        if borg_compat.check('V2'):
            cmd += ["-r", profile.repo.url, new_archive_name]
        else:
            cmd.append(f"{profile.repo.url}::{new_archive_name}")

        for f in SourceFileModel.select().where(SourceFileModel.profile == profile.id):
            cmd.append(f.dir)

        cmd += suffix_command

        ret['message'] = trans_late('messages', 'Starting backup…')
        ret['ok'] = True
        ret['cmd'] = cmd

        return ret
