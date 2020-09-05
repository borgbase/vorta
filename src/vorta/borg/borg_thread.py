import json
import os
import sys
import shutil
import shlex
import signal
import select
import time
import logging
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication
from subprocess import Popen, PIPE

from vorta.i18n import trans_late
from vorta.models import EventLogModel, BackupProfileMixin
from vorta.utils import keyring, borg_compat, pretty_bytes
from vorta.keyring.db import VortaDBKeyring

mutex = QtCore.QMutex()
logger = logging.getLogger(__name__)


class BorgThread(QtCore.QThread, BackupProfileMixin):
    """
    Base class to run `borg` command line jobs. If a command needs more pre- or post-processing
    it should subclass `BorgThread`.
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

        # Add extra Borg args to command. Never pass None.
        extra_args_str = params.get('extra_borg_arguments')
        if extra_args_str is not None and len(extra_args_str) > 0:
            extra_args = shlex.split(extra_args_str)
            cmd = cmd[:2] + extra_args + cmd[2:]

        env = os.environ.copy()
        env['BORG_HOSTNAME_IS_UNIQUE'] = '1'
        env['BORG_RELOCATED_REPO_ACCESS_IS_OK'] = '1'
        password = params.get('password')
        if password is not None:
            env['BORG_PASSPHRASE'] = password
        else:
            env['BORG_PASSPHRASE'] = '9999999'  # Set dummy password to avoid prompt.

        if env.get('BORG_PASSCOMMAND', False):
            env.pop('BORG_PASSPHRASE', None)  # Unset passphrase

        env['BORG_RSH'] = 'ssh -oStrictHostKeyChecking=no'
        ssh_key = params.get('ssh_key')
        if ssh_key is not None:
            ssh_key_path = os.path.expanduser(f'~/.ssh/{ssh_key}')
            env['BORG_RSH'] += f' -i {ssh_key_path}'

        self.env = env
        self.cmd = cmd
        self.cwd = params.get('cwd', None)
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
            ret['message'] = trans_late('messages', 'Backup is already in progress.')
            return ret

        if cls.prepare_bin() is None:
            ret['message'] = trans_late('messages', 'Borg binary was not found.')
            return ret

        if profile.repo is None:
            ret['message'] = trans_late('messages', 'Add a backup repository first.')
            return ret

        if not borg_compat.check('JSON_LOG'):
            ret['message'] = trans_late('messages', 'Your Borg version is too old. >=1.1.0 is required.')
            return ret

        # Try to get password from chosen keyring backend.
        logger.debug("Using %s keyring to store passwords.", keyring.__class__.__name__)
        ret['password'] = keyring.get_password('vorta-repo', profile.repo.url)

        # Try to fall back to DB Keyring, if we use the system keychain.
        if ret['password'] is None and keyring.is_primary:
            logger.debug('Password not found in primary keyring. Falling back to VortaDBKeyring.')
            ret['password'] = VortaDBKeyring().get_password('vorta-repo', profile.repo.url)

            # Give warning and continue if password is found there.
            if ret['password'] is not None:
                logger.warning('Found password in database, but secure storage was available. '
                               'Consider re-adding the repo to use it.')

        ret['ssh_key'] = profile.ssh_key
        ret['repo_id'] = profile.repo.id
        ret['repo_url'] = profile.repo.url
        ret['extra_borg_arguments'] = profile.repo.extra_borg_arguments
        ret['profile_name'] = profile.name

        ret['ok'] = True

        return ret

    @classmethod
    def prepare_bin(cls):
        """Find packaged borg binary. Prefer globally installed."""

        borg_in_path = shutil.which('borg')

        if borg_in_path:
            return borg_in_path
        elif sys.platform == 'darwin':
            # macOS: Look in pyinstaller bundle
            from Foundation import NSBundle
            mainBundle = NSBundle.mainBundle()

            bundled_borg = os.path.join(mainBundle.bundlePath(), 'Contents', 'Resources', 'borg-dir', 'borg.exe')
            if os.path.isfile(bundled_borg):
                return bundled_borg
        return None

    def run(self):
        self.started_event()
        mutex.lock()
        log_entry = EventLogModel(category='borg-run',
                                  subcommand=self.cmd[1],
                                  profile=self.params.get('profile_name', None)
                                  )
        log_entry.save()
        logger.info('Running command %s', ' '.join(self.cmd))

        p = Popen(self.cmd, stdout=PIPE, stderr=PIPE, bufsize=1, universal_newlines=True,
                  env=self.env, cwd=self.cwd, start_new_session=True)

        self.process = p

        # Prevent blocking of stdout/err. Via https://stackoverflow.com/a/7730201/3983708
        os.set_blocking(p.stdout.fileno(), False)
        os.set_blocking(p.stderr.fileno(), False)

        def read_async(fd):
            try:
                return fd.read()
            except (IOError, TypeError):
                return ''

        stdout = []
        while True:
            # Wait for new output
            select.select([p.stdout, p.stderr], [], [], 0.1)

            stdout.append(read_async(p.stdout))
            stderr = read_async(p.stderr)
            if stderr:
                for line in stderr.split('\n'):
                    try:
                        parsed = json.loads(line)
                        if parsed['type'] == 'log_message':
                            self.app.backup_log_event.emit(f'{parsed["levelname"]}: {parsed["message"]}')
                            level_int = getattr(logging, parsed["levelname"])
                            logger.log(level_int, parsed["message"])
                        elif parsed['type'] == 'file_status':
                            self.app.backup_log_event.emit(f'{parsed["path"]} ({parsed["status"]})')
                        elif parsed['type'] == 'archive_progress':
                            msg = (
                                f"Files: {parsed['nfiles']}, "
                                f"Original: {pretty_bytes(parsed['original_size'])}, "
                                f"Deduplicated: {pretty_bytes(parsed['deduplicated_size'])}, "
                                f"Compressed: {pretty_bytes(parsed['compressed_size'])}"
                            )
                            self.app.backup_progress_event.emit(msg)
                    except json.decoder.JSONDecodeError:
                        msg = line.strip()
                        if msg:  # Log only if there is something to log.
                            self.app.backup_log_event.emit(msg)
                            logger.warning(msg)

            if p.poll() is not None:
                time.sleep(0.1)
                stdout.append(read_async(p.stdout))
                break

        result = {
            'params': self.params,
            'returncode': self.process.returncode,
            'cmd': self.cmd,
        }
        stdout = ''.join(stdout)

        try:
            result['data'] = json.loads(stdout)
        except ValueError:
            result['data'] = stdout

        log_entry.returncode = p.returncode
        log_entry.repo_url = self.params.get('repo_url', None)
        log_entry.save()

        self.process_result(result)
        self.finished_event(result)
        mutex.unlock()

    def cancel(self):
        if self.isRunning():
            mutex.unlock()
            self.process.send_signal(signal.SIGINT)
            self.terminate()

    def process_result(self, result):
        pass

    def started_event(self):
        self.updated.emit(self.tr('Task started'))

    def finished_event(self, result):
        self.result.emit(result)
