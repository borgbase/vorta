import json
import os
import sys
import shutil
import signal
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication
from subprocess import Popen, PIPE

from ..models import SourceDirModel, BackupProfileModel, WifiSettingModel, EventLogModel, BackupProfileMixin
from ..utils import get_current_wifi, keyring

mutex = QtCore.QMutex()


class BorgThread(QtCore.QThread, BackupProfileMixin):
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
        :param params: Pass options that were used to build cmd and may be needed to
                       process the result.
        :param parent: Parent window. Needs `thread.wait()` if none. (scheduler)
        """

        super().__init__(parent)
        self.app = QApplication.instance()
        self.app.backup_cancelled_event.connect(self.cancel)

        cmd[0] = self.prepare_bin()

        env = os.environ.copy()
        env['BORG_HOSTNAME_IS_UNIQUE'] = '1'
        if params.get('password') and params['password'] is not None:
            env['BORG_PASSPHRASE'] = params['password']

        env['BORG_RSH'] = 'ssh -oStrictHostKeyChecking=no'
        if params.get('ssh_key') and params['ssh_key'] is not None:
            env['BORG_RSH'] += f' -i ~/.ssh/{params["ssh_key"]}'

        self.env = env
        self.cmd = cmd
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
    def prepare(cls, profile):
        """
        Prepare for running Borg. This function in the base class should be called from all
        subclasses and calls that define their own `cmd`.

        The `prepare()` step does these things:
        - validate if all conditions to run command are met
        - build borg command

        `prepare()` is run 2x. First at the global level and then for each subcommand.

        :return: dict(ok: book, message: str)
        """
        ret = {'ok': False}

        # Do checks to see if running Borg is possible.
        if cls.is_running():
            ret['message'] = 'Backup is already in progress.'
            return ret

        if cls.prepare_bin() is None:
            ret['message'] = 'Borg binary was not found.'
            return ret

        if profile.repo is None:
            ret['message'] = 'Add a remote backup repository first.'
            return ret

        ret['ssh_key'] = profile.ssh_key
        ret['repo_id'] = profile.repo.id
        ret['repo_url'] = profile.repo.url
        ret['profile_name'] = profile.name
        ret['password'] = keyring.get_password("vorta-repo", profile.repo.url)  # None if no password.
        ret['ok'] = True

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
        log_entry = EventLogModel(category='borg-run',
                                  subcommand=self.cmd[1],
                                  profile=self.params.get('profile_name', None)
                                  )
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
        log_entry.repo_url = self.params.get('repo_url', None)
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


class BorgThreadChain(BorgThread):
    """
    Metaclass of `BorgThread` that can run multiple other BorgThread actions while providing the same
    interface as a single action.
    """

    def __init__(self, cmds, input_values, parent=None):
        """
        Takes a list of tuples with `BorgThread` subclass and optional input parameters. Then all actions are exectuted
        and a merged result object is returned to the caller. If there is any error, then current result is returned.

        :param actions:
        :return: dict(results)
        """
        self.parent = parent
        self.threads = []
        self.combined_result = {}

        for cmd, input_value in zip(cmds, input_values):
            if input_value is not None:
                msg = cmd.prepare(input_value)
            else:
                msg = cmd.prepare()
            if msg['ok']:
                thread = cmd(msg['cmd'], msg, parent)
                thread.updated.connect(self.updated.emit)  # All log entries are immediately sent to the parent.
                thread.result.connect(self.partial_result)
                self.threads.append(thread)
        self.threads[0].start()

    def partial_result(self, result):
        if result['returncode'] == 0:
            self.combined_result.update(result)
            self.threads.pop(0)

            if len(self.threads) > 0:
                self.threads[0].start()
            else:
                self.result.emit(self.combined_result)
