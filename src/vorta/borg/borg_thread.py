import json
import os
import sys
import shutil
import signal
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication
from subprocess import Popen, PIPE

from vorta.models import SourceDirModel, BackupProfileModel, WifiSettingModel, EventLogModel
from vorta.utils import get_current_wifi, keyring

mutex = QtCore.QMutex()


class BorgThread(QtCore.QThread):
    """
    Base class to run `borg` command line jobs. If a command needs more pre- or past-processing
    it should sublass `BorgThread`.
    """

    updated = QtCore.pyqtSignal(str)
    result = QtCore.pyqtSignal(dict)

    def __init__(self, cmd, params, parent=None):
        """
        Thread to run Borg operations in.

        :param cmd: Borg command line
        :param params: To pass extra options that are later formatted centrally.
        :param parent: Parent window. Needs `thread.wait()` if none. (scheduler)
        """

        super().__init__(parent)
        self.app = QApplication.instance()
        self.app.backup_cancelled_event.connect(self.cancel)
        self.cmd = cmd

        self.cmd[0] = self.prepare_bin()

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
        if mutex.tryLock():
            mutex.unlock()
            return False
        else:
            return True

    @classmethod
    def prepare(cls):
        profile = BackupProfileModel.get(id=1)
        ret = {'ok': False}

        # Do checks to see if running Borg is possible.
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

        if cls.prepare_bin() is None:
            ret['message'] = 'Borg binary was not found.'
            return ret

        ret['params'] = {'password': keyring.get_password("vorta-repo", profile.repo.url)}

        return ret

    @classmethod
    def prepare_bin(cls):
        """Find packaged borg binary. Prefer globally installed."""

        # Look in current PATH.
        if shutil.which('borg'):
            return 'borg'
        else:
            # Look in pyinstaller package
            cwd = getattr(sys, '_MEIPASS', os.getcwd())
            meipass_borg = os.path.join(cwd, 'bin', 'borg')
            if os.path.isfile(meipass_borg):
                return meipass_borg
            else:
                return None

    def run(self):
        self.started_event()
        mutex.lock()
        log_entry = EventLogModel(category='borg-run', subcommand=self.cmd[1])
        log_entry.save()

        self.process = Popen(self.cmd, stdout=PIPE, stderr=PIPE, bufsize=1,
                             universal_newlines=True, env=self.env, preexec_fn=os.setsid)

        for line in iter(self.process.stderr.readline, ''):
            try:
                parsed = json.loads(line)
                if parsed['type'] == 'log_message':
                    self.log_event(f'{parsed["levelname"]}: {parsed["message"]}')
                elif parsed['type'] == 'file_status':
                    self.log_event(f'{parsed["path"]} ({parsed["status"]})')
            except json.decoder.JSONDecodeError:
                self.log_event(line.strip())

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

        self.process_result(result)
        self.finished_event(result)
        mutex.unlock()

    def cancel(self):
        if self.isRunning():
            mutex.unlock()
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.terminate()

    def process_result(self, result):
        pass

    def log_event(self, msg):
        self.updated.emit(msg)

    def started_event(self):
        self.updated.emit('Task started')

    def finished_event(self, result):
        self.result.emit(result)
