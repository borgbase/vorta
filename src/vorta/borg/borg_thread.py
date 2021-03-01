import json
import os
import sys
import shutil
import shlex
import signal
import select
import time
import logging
from collections import namedtuple
from threading import Lock
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication
from subprocess import Popen, PIPE, TimeoutExpired

from vorta.i18n import trans_late, translate
from vorta.models import EventLogModel, BackupProfileMixin
from vorta.utils import borg_compat, pretty_bytes
from vorta.keyring.abc import VortaKeyring
from vorta.keyring.db import VortaDBKeyring

mutex = Lock()
logger = logging.getLogger(__name__)

FakeRepo = namedtuple('Repo', ['url', 'id', 'extra_borg_arguments', 'encryption'])
FakeProfile = namedtuple('FakeProfile', ['repo', 'name', 'ssh_key'])


class BorgThread(QtCore.QThread, BackupProfileMixin):
    """
    Base class to run `borg` command line jobs. If a command needs more pre- or post-processing
    it should subclass `BorgThread`.
    """

    updated = QtCore.pyqtSignal(str)
    result = QtCore.pyqtSignal(dict)
    keyring = None  # Store keyring to minimize imports

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

        # Declare labels here for translation
        self.category_label = {"files": trans_late("BorgThread", "Files"),
                               "original": trans_late("BorgThread", "Original"),
                               "deduplicated": trans_late("BorgThread", "Deduplicated"),
                               "compressed": trans_late("BorgThread", "Compressed"), }

        cmd[0] = self.prepare_bin()

        # Add extra Borg args to command. Never pass None.
        extra_args_str = params.get('extra_borg_arguments')
        if extra_args_str is not None and len(extra_args_str) > 0:
            extra_args = shlex.split(extra_args_str)
            cmd = cmd[:2] + extra_args + cmd[2:]

        env = os.environ.copy()
        env['BORG_HOSTNAME_IS_UNIQUE'] = '1'
        env['BORG_RELOCATED_REPO_ACCESS_IS_OK'] = '1'
        env['BORG_RSH'] = 'ssh'

        if 'additional_env' in params:
            env = {**env, **params['additional_env']}

        password = params.get('password')
        if password is not None:
            env['BORG_PASSPHRASE'] = password
        else:
            env['BORG_PASSPHRASE'] = '9999999'  # Set dummy password to avoid prompt.

        if env.get('BORG_PASSCOMMAND', False):
            env.pop('BORG_PASSPHRASE', None)  # Unset passphrase

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
        return mutex.locked()

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
        cls.keyring = VortaKeyring.get_keyring()
        logger.debug("Using %s keyring to store passwords.", cls.keyring.__class__.__name__)
        ret['password'] = cls.keyring.get_password('vorta-repo', profile.repo.url)

        # Check if keyring is locked
        if profile.repo.encryption != 'none' and not cls.keyring.is_unlocked:
            ret['message'] = trans_late('messages',
                                        'Please unlock your system password manager or disable it under Misc')
            return ret

        # Try to fall back to DB Keyring, if we use the system keychain.
        if ret['password'] is None and cls.keyring.is_system:
            logger.debug('Password not found in primary keyring. Falling back to VortaDBKeyring.')
            ret['password'] = VortaDBKeyring().get_password('vorta-repo', profile.repo.url)

            # Give warning and continue if password is found there.
            if ret['password'] is not None:
                logger.warning('Found password in database, but secure storage was available. '
                               'Consider re-adding the repo to use it.')

        # Password is required for encryption, cannot continue
        if ret['password'] is None and not isinstance(profile.repo, FakeRepo) and profile.repo.encryption != 'none':
            ret['message'] = trans_late(
                'messages', "Your repo passphrase was stored in a password manager which is no longer available.\n"
                "Try unlinking and re-adding your repo.")
            return ret

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
        mutex.acquire()
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
                            context = {
                                'msgid': parsed.get('msgid'),
                                'repo_url': self.params['repo_url'],
                                'profile_name': self.params.get('profile_name'),
                                'cmd': self.params['cmd'][1]
                            }
                            self.app.backup_log_event.emit(
                                f'{parsed["levelname"]}: {parsed["message"]}', context)
                            level_int = getattr(logging, parsed["levelname"])
                            logger.log(level_int, parsed["message"])
                        elif parsed['type'] == 'file_status':
                            self.app.backup_log_event.emit(f'{parsed["path"]} ({parsed["status"]})', {})
                        elif parsed['type'] == 'archive_progress':
                            msg = (
                                f"{translate('BorgThread','Files')}: {parsed['nfiles']}, "
                                f"{translate('BorgThread','Original')}: {pretty_bytes(parsed['original_size'])}, "
                                f"{translate('BorgThread','Deduplicated')}: {pretty_bytes(parsed['deduplicated_size'])}, "  # noqa: E501
                                f"{translate('BorgThread','Compressed')}: {pretty_bytes(parsed['compressed_size'])}"
                            )
                            self.app.backup_progress_event.emit(msg)
                    except json.decoder.JSONDecodeError:
                        msg = line.strip()
                        if msg:  # Log only if there is something to log.
                            self.app.backup_log_event.emit(msg, {})
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
        mutex.release()

    def cancel(self):
        """
        First try to terminate the running Borg process with SIGINT (Ctrl-C),
        if this fails, use SIGTERM.
        """
        if self.isRunning():
            self.process.send_signal(signal.SIGINT)
            try:
                self.process.wait(timeout=3)
            except TimeoutExpired:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.quit()
            self.wait()
            if mutex.locked():
                mutex.release()

    def process_result(self, result):
        pass

    def started_event(self):
        self.updated.emit(self.tr('Task started'))

    def finished_event(self, result):
        self.result.emit(result)
