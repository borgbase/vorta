from __future__ import annotations

import json
import logging
import os
import select
import shlex
import shutil
import signal
import sys
import time
import traceback
from collections import namedtuple
from datetime import datetime as dt
from subprocess import PIPE, Popen, TimeoutExpired
from threading import Lock
from typing import TYPE_CHECKING, Optional

from PyQt6 import QtCore
from PyQt6.QtCore import QT_TRANSLATE_NOOP
from PyQt6.QtWidgets import QApplication

if TYPE_CHECKING:
    from vorta import application
from vorta.borg.jobs_manager import JobInterface, report_exception_to_main_thread
from vorta.i18n import translate
from vorta.inhibitor.abc import Inhibitor
from vorta.keyring.abc import VortaKeyring
from vorta.keyring.db import VortaDBKeyring
from vorta.store.models import EventLogModel, RepoModel, db_lock
from vorta.utils import borg_compat, pretty_bytes

keyring_lock = Lock()
logger = logging.getLogger(__name__)

FakeRepo = namedtuple('Repo', ['url', 'name', 'id', 'extra_borg_arguments', 'encryption'])
FakeProfile = namedtuple('FakeProfile', ['id', 'repo', 'name', 'ssh_key'])

TRACEBACK_HEADER = 'Traceback (most recent call last):'

# Return code reported when a job raised in Vorta. Same as Borg's error code; results
# from such a job also carry an `exception` key.
JOB_EXCEPTION_RETURNCODE = 2


def invalidate_repo_stats(repo_id: int) -> None:
    """Mark cached statistics unknown after a potentially partial repository change."""
    repo = RepoModel.get(id=repo_id)
    repo.total_size = None
    repo.unique_csize = None
    repo.unique_size = None
    repo.total_unique_chunks = None
    repo.save()


def summarize_traceback(message: str) -> str:
    """
    Borg logs unexpected errors as a full Python traceback, followed by system info.
    Return only the line with the exception, e.g. `PermissionError: [Errno 13] Permission denied: '/repo'`,
    so it can be shown to the user. Other messages are returned unchanged.
    """
    if not message.startswith(TRACEBACK_HEADER):
        return message

    # With chained exceptions, the last traceback has the exception that was raised in the end.
    last_traceback = message.rsplit(TRACEBACK_HEADER, 1)[1]
    for line in last_traceback.splitlines():
        # The lines of the stack frames are indented, the exception line is not.
        if line.strip() and not line[0].isspace():
            return line
    return message


"""
All methods in this class must be thread safe. Particularly,
I strongly unadvised global variable and class variables.
Sqlite access are thread-safe because peewee is thread-safe.
The method prepare is not thread-safe because of keyring and I don't know why. That's why I added a
temporary mutex.
"""


class BorgJob(JobInterface):
    """
    Base class to run `borg` command line jobs. If a command needs more pre- or post-processing
    it should subclass `BorgJob`.
    """

    updated = QtCore.pyqtSignal(str)
    result = QtCore.pyqtSignal(dict)
    keyring = None  # Store keyring to minimize imports
    should_inhibit = False
    emits_backup_finished = False  # True for job types that emit app.backup_finished_event

    # Per-run state, reset in run(). Class defaults keep the helpers safe without run().
    _result_emitted = False
    _backup_finished_emitted = False

    def __init__(self, cmd, params, site="default"):
        """
        Thread to run Borg operations in.

        :param cmd: Borg command line
        :param params: Pass options that were used to build cmd and may be needed to
                       process the result.
        :param site: For scheduler. Only one job can run per site at one time. Site is
                     usually the repository ID, or 'default' for misc Borg commands.
        """

        super().__init__()
        self.site_id = site
        self.app: application.VortaApp = QApplication.instance()

        # Declare labels here for translation
        self.category_label = {
            "files": QT_TRANSLATE_NOOP("BorgJob", "Files"),
            "original": QT_TRANSLATE_NOOP("BorgJob", "Original"),
            "deduplicated": QT_TRANSLATE_NOOP("BorgJob", "Deduplicated"),
            "compressed": QT_TRANSLATE_NOOP("BorgJob", "Compressed"),
        }

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
            # Without IdentitiesOnly, SSH tries every key in the agent before this one (#2331).
            env['BORG_RSH'] += f' -i {ssh_key_path} -o IdentitiesOnly=yes'

        self.env = env
        self.cmd = cmd
        self.cwd = params.get('cwd', None)
        self.params = params
        self.process = None
        self.cleanup_files = params.get('cleanup_files', [])

    def repo_id(self):
        return self.site_id

    def cancel(self):
        logger.debug("Cancel job on site %s", self.site_id)
        if self.process is not None:
            self.process.send_signal(signal.SIGINT)
            try:
                self.process.wait(timeout=3)
            except TimeoutExpired:
                try:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                except ProcessLookupError:
                    pass

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

        if cls.prepare_bin() is None:
            ret['message'] = QT_TRANSLATE_NOOP('messages', 'Borg binary was not found.')
            return ret

        if profile.repo is None:
            ret['message'] = QT_TRANSLATE_NOOP('messages', 'Select a backup repository first.')
            return ret

        if not borg_compat.check('JSON_LOG'):
            ret['message'] = QT_TRANSLATE_NOOP('messages', 'Your Borg version is too old. >=1.1.0 is required.')
            return ret

        # Try to get password from chosen keyring backend.
        with keyring_lock:
            cls.keyring = VortaKeyring.get_keyring()
            logger.debug("Using %s keyring to store passwords.", cls.keyring.__class__.__name__)
            encrypted = profile.repo.encryption != 'none'
            if encrypted and not cls.keyring.try_unlock():
                ret['message'] = QT_TRANSLATE_NOOP(
                    'messages',
                    'Please unlock your system password manager or disable it under Settings',
                )
                return ret
            # Unencrypted repos don't need a passphrase, so don't prompt to read one.
            if encrypted or cls.keyring.is_unlocked:
                ret['password'] = cls.keyring.get_password('vorta-repo', profile.repo.url)
            else:
                ret['password'] = None

            # Try to fall back to DB Keyring, if we use the system keychain.
            if ret['password'] is None and cls.keyring.is_system:
                logger.debug('Password not found in primary keyring. Falling back to VortaDBKeyring.')
                ret['password'] = VortaDBKeyring().get_password('vorta-repo', profile.repo.url)

                # Give warning and continue if password is found there.
                if ret['password'] is not None:
                    logger.warning(
                        'Found password in database, but secure storage was available. '
                        'Consider re-adding the repo to use it.'
                    )

        # Password is required for encryption, cannot continue
        if ret['password'] is None and not isinstance(profile.repo, FakeRepo) and profile.repo.encryption != 'none':
            ret['message'] = QT_TRANSLATE_NOOP(
                'messages',
                "Your repo passphrase was stored in a password manager which is no longer available.\n"
                "Try unlinking and re-adding your repo.",
            )
            return ret

        ret['ssh_key'] = profile.ssh_key
        ret['repo_id'] = profile.repo.id
        ret['repo_url'] = profile.repo.url
        ret['repo_name'] = profile.repo.name
        ret['extra_borg_arguments'] = profile.repo.extra_borg_arguments
        ret['profile_name'] = profile.name
        ret['profile_id'] = profile.id

        ret['ok'] = True
        ret['cleanup_files'] = []

        return ret

    @classmethod
    def prepare_bin(cls):
        """Find packaged borg binary. Prefer globally installed."""
        # On MacOS, the PATH environment variable does not seem to be set when run as a pyinstaller binary.
        # More info at https://github.com/borgbase/vorta/issues/2100
        # Set the path to also find homebrew installs of Borg, and avoid falling back to the embedded binary.
        if sys.platform == 'darwin':
            # This runs for every job, so only add the directories that are still missing.
            path_dirs = os.environ.get("PATH", "/usr/bin:/bin").split(os.pathsep)
            missing_dirs = [d for d in ("/opt/homebrew/bin", "/usr/local/bin") if d not in path_dirs]
            if missing_dirs:
                os.environ["PATH"] = os.pathsep.join(path_dirs + missing_dirs)
        # Now continue looking for the borg binary to use
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
        self._result_emitted = False
        self._backup_finished_emitted = False
        self._process_result_entered = False
        self._finished_event_entered = False
        self._log_entry = None
        self._log_entry_final_saved = False
        self._error_messages = []
        self.process = None
        try:
            with self.get_inhibitor():
                self._run()
        except Exception as exc:
            # Handled here, outside _run's `with db_lock:`, because db_lock is not reentrant.
            self._finish_after_exception(exc)
        finally:
            self._close_cleanup_files()

    def _close_cleanup_files(self):
        for tmpfile in self.cleanup_files:
            try:
                tmpfile.close()
            except Exception:
                logger.exception('Could not close temporary file of %s', type(self).__name__)

    def _finish_after_exception(self, exc):
        """
        Finish a job that raised, so the UI, scheduler and event log see it end.

        Slow steps run before the result is emitted: the main window only re-enables its
        buttons if the worker is no longer running when it handles the result.
        """
        job_name = type(self).__name__
        logger.error('%s raised an unexpected exception', job_name, exc_info=exc)
        tb_text = ''.join(traceback.format_exception(exc))
        try:
            # First line only: some messages, like peewee's DoesNotExist, carry the SQL on further lines.
            summary = f'{type(exc).__name__}: {exc}'.splitlines()[0]
        except Exception:
            summary = type(exc).__name__

        try:
            process = self.process
            if process is not None and process.poll() is None:
                self.cancel()
                try:
                    process.wait(timeout=5)
                except TimeoutExpired:
                    logger.warning('Borg process of %s did not exit after cancel', job_name)
        except Exception:
            logger.exception('Could not stop the Borg process of %s', job_name)

        log_entry = self._log_entry
        if log_entry is not None and not self._log_entry_final_saved:
            try:
                log_entry.returncode = JOB_EXCEPTION_RETURNCODE
                log_entry.end_time = dt.now()
                log_entry.repo_url = self.params.get('repo_url')
                with db_lock:
                    log_entry.save()
            except Exception:
                logger.exception('Could not save the event log entry of %s', job_name)

        self._close_cleanup_files()

        fail_result = {
            'params': self.params,
            'cmd': self.cmd,
            'returncode': JOB_EXCEPTION_RETURNCODE,
            'errors': [*self._error_messages, (logging.CRITICAL, summary)],
            'data': {},
            'log_entry_id': log_entry.id if log_entry is not None else None,
            'exception': summary,
        }

        # Failed prune/delete jobs must still invalidate stats, but never retry a result handler that raised.
        if not self._process_result_entered:
            self._process_result_entered = True
            try:
                with db_lock:
                    self.process_result(fail_result)
            except Exception:
                logger.exception('process_result of %s raised while handling an exception', job_name)

        if not self._finished_event_entered:
            self._finished_event_entered = True
            try:
                self.finished_event(fail_result)
            except Exception:
                logger.exception('finished_event of %s raised while handling an exception', job_name)

        # Some finished_event implementations post success-sounding text, so say it failed last.
        try:
            profile_name = self.params.get('profile_name')
            prefix = f'[{profile_name}] ' if profile_name else ''
            self.app.backup_progress_event.emit(prefix + self.tr('Task failed: {}').format(summary))
        except Exception:
            logger.exception('Could not report the failure of %s', job_name)

        for emit in (self._emit_backup_finished, self._emit_result):
            try:
                emit(fail_result)
            except Exception:
                logger.exception('Could not emit the failure result of %s', job_name)

        report_exception_to_main_thread(tb_text)

    def _run(self):
        self.started_event()
        with db_lock:
            log_entry = EventLogModel(
                category=self.params.get('category', 'user'),
                subcommand=self.cmd[1],
                profile=self.params.get('profile_id', None),
            )
            log_entry.save()
            self._log_entry = log_entry

            # logs: put cmd arguments with special strings in quotation marks
            quote_strings = [' ', '*', '?', 're:']
            cmd_args_to_log = self.cmd[:]
            for i, arg in enumerate(cmd_args_to_log):
                if any(quotestr in arg for quotestr in quote_strings):
                    cmd_args_to_log[i] = "'" + arg + "'"  # add quotes

            logger.info('Running command: %s', ' '.join(cmd_args_to_log))
            del cmd_args_to_log

        p = Popen(
            self.cmd,
            stdout=PIPE,
            stderr=PIPE,
            bufsize=1,
            universal_newlines=True,
            env=self.env,
            cwd=self.cwd,
            start_new_session=True,
        )
        error_messages = []  # List of error messages included in the result
        self._error_messages = error_messages

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
                            message = summarize_traceback(parsed['message'])
                            context = {
                                'msgid': parsed.get('msgid'),
                                'message': parsed.get('message', ''),
                                'repo_url': self.params['repo_url'],
                                'profile_name': self.params.get('profile_name'),
                                'cmd': self.params['cmd'][1],
                            }
                            self.app.backup_log_event.emit(
                                f'[{self.params["profile_name"]}] {parsed["levelname"]}: {message}', context
                            )
                            level_int = getattr(logging, parsed["levelname"])
                            logger.log(level_int, parsed["message"])

                            if level_int >= logging.WARNING:
                                # Append log to list of error messages
                                error_messages.append((level_int, message))

                        elif parsed['type'] == 'file_status':
                            self.app.backup_log_event.emit(
                                f'[{self.params["profile_name"]}] {parsed["path"]} ({parsed["status"]})', {}
                            )
                        elif parsed['type'] == 'progress_percent' and parsed.get("message"):
                            self.app.backup_log_event.emit(f'[{self.params["profile_name"]}] {parsed["message"]}', {})
                        elif parsed['type'] == 'archive_progress' and not parsed.get('finished', False):
                            msg = (
                                f"{translate('BorgJob', 'Files')}: {parsed['nfiles']}, "
                                f"{translate('BorgJob', 'Original')}: {pretty_bytes(parsed['original_size'])}, "
                                # f"{translate('BorgJob','Compressed')}: {pretty_bytes(parsed['compressed_size'])}, " # noqa: E501
                                f"{translate('BorgJob', 'Deduplicated')}: {pretty_bytes(parsed.get('deduplicated_size', 0))}"  # noqa: E501
                            )
                            self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {msg}")
                    except json.decoder.JSONDecodeError:
                        msg = line.strip()
                        if msg:  # Log only if there is something to log.
                            self.app.backup_log_event.emit(f'[{self.params["profile_name"]}] {msg}', {})
                            logger.warning(msg)

            if p.poll() is not None:
                time.sleep(0.1)
                stdout.append(read_async(p.stdout))
                break

        result = {
            'params': self.params,
            'returncode': self.process.returncode,
            'cmd': self.cmd,
            'errors': error_messages,
        }
        stdout = ''.join(stdout)

        try:
            result['data'] = json.loads(stdout)
        except ValueError:
            result['data'] = stdout

        log_entry.returncode = p.returncode
        log_entry.repo_url = self.params.get('repo_url', None)
        log_entry.end_time = dt.now()
        result['log_entry_id'] = log_entry.id

        with db_lock:
            log_entry.save()
            self._log_entry_final_saved = True
            self._process_result_entered = True
            self.process_result(result)

        self._finished_event_entered = True
        self.finished_event(result)

    def process_result(self, result):
        pass

    def started_event(self):
        self.updated.emit(self.tr('Task started'))

    def finished_event(self, result):
        self._emit_result(result)

    def _emit_backup_finished(self, result):
        if not self.emits_backup_finished or self._backup_finished_emitted:
            return
        self._backup_finished_emitted = True
        self.app.backup_finished_event.emit(result)

    def _emit_result(self, result):
        if self._result_emitted:
            return
        self._result_emitted = True
        self.result.emit(result)

    def get_inhibitor(self) -> Inhibitor:
        if self.should_inhibit:
            logger.debug("job will inhibit")
            return Inhibitor.get_inhibitor(f"borg {self.cmd[1]}")
        else:
            logger.debug("job will not inhibit")
            return Inhibitor.get_noop_inhibitor()
