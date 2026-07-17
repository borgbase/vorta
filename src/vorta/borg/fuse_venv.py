"""
Managed Python environment used only for `borg mount` on macOS.

Vorta's bundled Borg binary cannot ship FUSE support on macOS (notarization
restrictions prevent dynamically loading macFUSE/FUSE-T libraries). Building
Borg from source via pip inside a private virtualenv links against whatever
FUSE implementation is already installed and produces a mount-capable binary.

This module owns the venv location, readiness checks and the background job
that builds it. Only `BorgMountJob` consults it; all other Borg commands keep
using the normal binary resolution in `BorgJob.prepare_bin()`.
"""

import logging
import os
import shutil
import signal
import subprocess
import sys
from collections import deque
from pathlib import Path
from subprocess import PIPE, STDOUT, Popen, TimeoutExpired

from PyQt6 import QtCore

from vorta import config
from vorta.borg.jobs_manager import JobInterface

logger = logging.getLogger(__name__)

#: JobsManager site for setup jobs, so they never queue behind repo jobs.
SETUP_JOB_SITE = 'vorta-fuse-venv'

#: Written only after the built venv passed validation. A partially built
#: venv (failed or cancelled pip install) never has this file.
MARKER_FILE = '.venv-ready'


def is_supported() -> bool:
    """This workaround only makes sense on macOS."""
    return sys.platform == 'darwin'


def venv_path() -> Path:
    """Fixed venv location inside Vorta's own application support directory."""
    return Path(config.SETTINGS_DIR) / 'borg-fuse-venv'


def venv_borg_bin() -> Path:
    return venv_path() / 'bin' / 'borg'


def is_venv_ready() -> bool:
    """
    Cheap check used at mount time and for UI state.

    The marker file is only written after a successful build was validated
    (borg runs and llfuse imports), so checking marker + executable is enough
    here without spawning subprocesses on every call.
    """
    return (venv_path() / MARKER_FILE).is_file() and os.access(venv_borg_bin(), os.X_OK)


def find_system_python() -> str:
    """
    Find a Python interpreter to create the venv with.

    `sys.executable` is the Vorta app binary when running from the bundled
    `.app`, so it cannot be used here.
    """
    candidates = [
        shutil.which('python3'),
        '/opt/homebrew/bin/python3',
        '/usr/local/bin/python3',
        '/usr/bin/python3',
    ]
    for candidate in candidates:
        if candidate and os.access(candidate, os.X_OK):
            return candidate
    return None


def find_pkg_config() -> str:
    candidates = [
        shutil.which('pkg-config'),
        '/opt/homebrew/bin/pkg-config',
        '/usr/local/bin/pkg-config',
    ]
    for candidate in candidates:
        if candidate and os.access(candidate, os.X_OK):
            return candidate
    return None


class FuseVenvSetupJob(JobInterface):
    """
    Build (or rebuild) the managed mount venv in a background worker.

    Runs via `JobsManager` under its own site, streaming one-line progress
    through `updated` and finishing with `result` = {'ok': bool, 'message': str,
    'borg_version': str}. Never installs anything outside the venv directory;
    missing system tools (pkg-config, Xcode CLT) are reported with the exact
    command for the user to run themselves.
    """

    updated = QtCore.pyqtSignal(str)
    result = QtCore.pyqtSignal(dict)

    def __init__(self, rebuild=False):
        super().__init__()
        self.rebuild = rebuild
        self.process = None
        self._cancelled = False
        self._output_tail = deque(maxlen=40)  # last lines, for error diagnosis

    def repo_id(self):
        return SETUP_JOB_SITE

    def cancel(self):
        self._cancelled = True
        if self.process is not None:
            self.process.send_signal(signal.SIGINT)
            try:
                self.process.wait(timeout=3)
            except TimeoutExpired:
                try:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                except ProcessLookupError:
                    pass

    def run(self):
        path = venv_path()
        marker = path / MARKER_FILE
        # A rebuild in progress must never count as ready.
        if marker.exists():
            marker.unlink()

        try:
            self._build()
        except _SetupError as e:
            logger.warning('Mount venv setup failed: %s', e)
            self.result.emit({'ok': False, 'message': str(e), 'borg_version': ''})
        except Exception as e:
            logger.exception('Unexpected error during mount venv setup')
            self.result.emit({'ok': False, 'message': str(e), 'borg_version': ''})

    def _build(self):
        path = venv_path()

        python = find_system_python()
        if python is None:
            raise _SetupError(
                self.tr(
                    'No python3 interpreter found. Install the Xcode Command Line Tools '
                    '(xcode-select --install) or Python via Homebrew, then try again.'
                )
            )

        # Detect the known pkg-config failure mode up front instead of letting
        # pip fail later with an opaque compiler traceback.
        if find_pkg_config() is None:
            raise _SetupError(
                self.tr(
                    'pkg-config is required to build Borg but was not found. '
                    'Install it with "brew install pkg-config" and try again.'
                )
            )

        if self.rebuild:
            self.updated.emit(self.tr('Rebuilding environment in {0}…').format(str(path)))
        else:
            self.updated.emit(self.tr('Creating environment in {0}…').format(str(path)))
        # --clear empties a pre-existing venv, so repeated runs start clean.
        self._run_step([python, '-m', 'venv', '--clear', str(path)])

        pip = str(path / 'bin' / 'pip')
        self.updated.emit(self.tr('Updating packaging tools…'))
        self._run_step([pip, 'install', '--upgrade', 'pip', 'setuptools', 'wheel'])

        self.updated.emit(self.tr('Building Borg with FUSE support (this can take a few minutes)…'))
        self._run_step([pip, 'install', 'borgbackup[llfuse]'])

        self.updated.emit(self.tr('Verifying environment…'))
        borg_version = self._run_step([str(venv_borg_bin()), '--version'], capture=True).strip()
        self._run_step([str(path / 'bin' / 'python'), '-c', 'import llfuse'])

        (path / MARKER_FILE).write_text(borg_version)
        logger.info('Managed mount environment ready: %s', borg_version)
        self.result.emit({'ok': True, 'message': '', 'borg_version': borg_version})

    def _run_step(self, cmd, capture=False):
        """Run one subprocess, streaming output. Raises _SetupError on failure."""
        if self._cancelled:
            raise _SetupError(self.tr('Cancelled.'))

        logger.info('Running command: %s', ' '.join(cmd))
        env = os.environ.copy()
        # Match BorgJob.prepare_bin(): the bundled app may miss Homebrew paths,
        # which pip needs to find pkg-config during the build.
        env['PATH'] = f"{env.get('PATH', '/usr/bin:/bin')}:/opt/homebrew/bin:/usr/local/bin"

        p = Popen(
            cmd,
            stdout=PIPE,
            stderr=STDOUT,
            bufsize=1,
            universal_newlines=True,
            env=env,
            start_new_session=True,
        )
        self.process = p

        output = []
        for line in p.stdout:
            line = line.rstrip()
            if line:
                self._output_tail.append(line)
                if capture:
                    output.append(line)
                else:
                    self.updated.emit(line)
        p.wait()
        self.process = None

        if self._cancelled:
            raise _SetupError(self.tr('Cancelled.'))
        if p.returncode != 0:
            raise _SetupError(self._diagnose_failure(cmd))
        return '\n'.join(output)

    def _diagnose_failure(self, cmd):
        """Turn known build failures into actionable messages instead of a pip traceback."""
        tail = '\n'.join(self._output_tail)
        lowered = tail.lower()
        if 'pkg-config' in lowered:
            return self.tr(
                'The build failed because pkg-config is missing. '
                'Install it with "brew install pkg-config" and try again.'
            )
        if 'xcrun' in lowered or 'command line tools' in lowered or 'xcode-select' in lowered:
            return self.tr(
                'The build failed because the Xcode Command Line Tools are missing. '
                'Install them with "xcode-select --install" and try again.'
            )
        last_lines = '\n'.join(list(self._output_tail)[-5:])
        return self.tr('Setup failed running {0}:\n{1}').format(' '.join(cmd), last_lines)


class _SetupError(Exception):
    """A setup step failed with a message meant for the user."""
