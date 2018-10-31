import json
import os
import sys
import shutil
import tempfile
import platform
import keyring
from dateutil import parser
from datetime import datetime as dt
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication
from subprocess import Popen, PIPE

from .models import SourceDirModel, BackupProfileModel, EventLogModel, WifiSettingModel, SnapshotModel, BackupProfileMixin
from .utils import get_current_wifi



class BorgThread(QtCore.QThread, BackupProfileMixin):
    updated = QtCore.pyqtSignal(str)
    result = QtCore.pyqtSignal(object)
    mutex = QtCore.QMutex()

    def __init__(self, cmd, params, parent=None):
        """
        Thread to run Borg operations in.

        :param cmd: Borg command line
        :param params: To pass extra options that are later formatted centrally.
        :param parent: Parent window. Needs `thread.wait()` if none.
        """
        super().__init__(parent)

        # Find packaged borg binary. Prefer globally installed.
        if not shutil.which('borg'):
            meipass_borg = os.path.join(sys._MEIPASS, 'bin', 'borg')
            if os.path.isfile(meipass_borg):
                cmd[0] = meipass_borg
        self.cmd = cmd

        env = os.environ.copy()
        env['BORG_HOSTNAME_IS_UNIQUE'] = '1'
        if params.get('password') and params['password'] is not None:
            env['BORG_PASSPHRASE'] = params['password']

        env['BORG_RSH'] = 'ssh -oStrictHostKeyChecking=no'
        if params.get('ssh_key') and params['ssh_key']:
            env['BORG_RSH'] += f' -i ~/.ssh/{params["ssh_key"]}'

        self.env = env
        self.params = params
        self.process = None

    @classmethod
    def is_running(cls):
        if cls.mutex.tryLock():
            cls.mutex.unlock()
            return False
        else:
            return True

    def run(self):
        self.mutex.lock()
        log_entry = EventLogModel(category='borg-run', subcommand=self.cmd[1])
        log_entry.save()
        self.process = Popen(self.cmd, stdout=PIPE, stderr=PIPE, bufsize=1, universal_newlines=True, env=self.env)
        for line in iter(self.process.stderr.readline, ''):
            try:
                parsed = json.loads(line)
                if parsed['type'] == 'log_message':
                    self.updated.emit(f'{parsed["levelname"]}: {parsed["message"]}')
                elif parsed['type'] == 'file_status':
                    self.updated.emit(f'{parsed["path"]} ({parsed["status"]})')
            except json.decoder.JSONDecodeError:
                self.updated.emit(line.strip())

        self.process.wait()
        stdout = self.process.stdout.read()
        result = {
            'params': self.params,
            'returncode': self.process.returncode,
            'cmd': self.cmd
        }
        try:
            result['data'] = json.loads(stdout)
        except:
            result['data'] = {}

        log_entry.returncode = self.process.returncode
        log_entry.save()

        # If result function is available for subcommand, run it.
        result_func = f'process_{self.cmd[1]}_result'
        if hasattr(self, result_func):
            getattr(self, result_func)(result)

        self.result.emit(result)
        self.mutex.unlock()


    def process_create_result(self, result):
        if result['returncode'] == 0:
            new_snapshot, created = SnapshotModel.get_or_create(
                snapshot_id=result['data']['archive']['id'],
                defaults={
                    'name': result['data']['archive']['name'],
                    'time': parser.parse(result['data']['archive']['start']),
                    'repo': self.profile.repo
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

    @classmethod
    def prepare_runner(cls):
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


