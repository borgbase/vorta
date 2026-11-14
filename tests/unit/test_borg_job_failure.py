"""A job that raises still finishes: one result, an event log entry, and the traceback reported (#2600)."""

import logging
import signal
import sys
import tempfile
import threading
import time
import types
from unittest.mock import MagicMock

import pytest
from PyQt6 import QtCore

import vorta.application
import vorta.borg.borg_job
from vorta.__main__ import thread_exception_hook
from vorta.borg.borg_job import JOB_EXCEPTION_RETURNCODE
from vorta.borg.break_lock import BorgBreakJob
from vorta.borg.check import BorgCheckJob
from vorta.borg.prune import BorgPruneJob
from vorta.borg.rename import BorgRenameJob
from vorta.store.models import BackupProfileModel, EventLogModel

RESULT_KEYS = {'params', 'cmd', 'returncode', 'errors', 'data', 'log_entry_id', 'exception'}


@pytest.fixture
def profile():
    return BackupProfileModel.select().first()


@pytest.fixture
def popen_raises(mocker):
    return mocker.patch.object(
        vorta.borg.borg_job, 'Popen', side_effect=FileNotFoundError(2, 'No such file or directory', 'borg')
    )


@pytest.fixture
def emitted(qapp):
    """Record what a job run synchronously emits. Its signals are delivered directly."""
    recorded = {'backup_finished': [], 'progress': [], 'check_failed': []}
    connections = [
        (qapp.backup_finished_event, recorded['backup_finished'].append),
        (qapp.backup_progress_event, recorded['progress'].append),
        (qapp.check_failed_event, recorded['check_failed'].append),
    ]
    for signal_, slot in connections:
        signal_.connect(slot)
    yield recorded
    for signal_, slot in connections:
        signal_.disconnect(slot)


def run_job(job_class, params, emitted):
    job = job_class(params['cmd'], params, params['repo_id'])
    results = []
    job.result.connect(results.append)
    job.run()
    return results


def test_popen_error_finishes_the_job(qapp, profile, popen_raises, emitted, caplog):
    params = BorgPruneJob.prepare(profile)

    with caplog.at_level(logging.ERROR):
        results = run_job(BorgPruneJob, params, emitted)

    assert len(results) == 1
    assert len(emitted['backup_finished']) == 1
    result = results[0]
    assert emitted['backup_finished'][0] is result
    assert RESULT_KEYS <= result.keys()
    assert result['returncode'] == JOB_EXCEPTION_RETURNCODE
    assert result['errors'][-1] == (logging.CRITICAL, result['exception'])
    assert result['exception'].startswith('FileNotFoundError: ')
    assert result['data'] == {}

    log_entry = EventLogModel.get_by_id(result['log_entry_id'])
    assert log_entry.returncode == JOB_EXCEPTION_RETURNCODE
    assert log_entry.repo_url == params['repo_url']
    assert log_entry.end_time >= log_entry.start_time

    assert any('BorgPruneJob' in r.getMessage() and r.exc_info for r in caplog.records)


def test_cleanup_files_are_closed_on_exception(qapp, profile, popen_raises, emitted):
    params = BorgPruneJob.prepare(profile)
    tmpfile = tempfile.NamedTemporaryFile(mode='w+')
    params['cleanup_files'] = [tmpfile]

    run_job(BorgPruneJob, params, emitted)

    assert tmpfile.closed


def test_slow_work_is_done_before_the_result_is_emitted(qapp, profile, mocker, tmp_path):
    """The main window only unblocks if the worker is idle when it handles the result, so nothing slow may follow."""
    (tmp_path / 'stdout').write_text('')
    (tmp_path / 'stderr').write_text('0\n')
    tmpfile = tempfile.NamedTemporaryFile(mode='w+')
    params = BorgPruneJob.prepare(profile)
    params['cleanup_files'] = [tmpfile]
    seen = []

    with open(tmp_path / 'stdout') as stdout, open(tmp_path / 'stderr') as stderr:
        process = MagicMock(stdout=stdout, stderr=stderr, returncode=None)
        process.poll.return_value = None
        mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=process)

        def at_emission(result):
            log_entry = EventLogModel.get_by_id(result['log_entry_id'])
            seen.append((tmpfile.closed, log_entry.returncode, process.send_signal.called, process.wait.called))

        qapp.backup_finished_event.connect(at_emission)
        try:
            job = BorgPruneJob(params['cmd'], params, params['repo_id'])
            job.result.connect(at_emission)
            job.run()
        finally:
            qapp.backup_finished_event.disconnect(at_emission)

    assert seen == [(True, JOB_EXCEPTION_RETURNCODE, True, True)] * 2


def test_unexpected_stderr_json_stops_borg(qapp, profile, mocker, emitted, tmp_path):
    """Valid JSON that is not a log dict raises in the stderr parser; the still running Borg is stopped."""
    (tmp_path / 'stdout').write_text('')
    (tmp_path / 'stderr').write_text('0\n{}\n')
    with open(tmp_path / 'stdout') as stdout, open(tmp_path / 'stderr') as stderr:
        process = MagicMock(stdout=stdout, stderr=stderr, returncode=None)
        process.poll.return_value = None
        mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=process)

        results = run_job(BorgPruneJob, BorgPruneJob.prepare(profile), emitted)

    assert len(results) == 1
    assert results[0]['returncode'] == JOB_EXCEPTION_RETURNCODE
    assert results[0]['exception'].startswith('TypeError: ')
    process.send_signal.assert_any_call(signal.SIGINT)


def test_finished_event_raising_before_its_emits(qapp, profile, mocker, borg_json_output, emitted):
    """Prune looks up the repo before emitting. A missing repo still ends with one failure result."""
    stdout, stderr = borg_json_output('prune')
    mocker.patch.object(
        vorta.borg.borg_job, 'Popen', return_value=MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    )
    params = BorgPruneJob.prepare(profile)
    params['repo_id'] = 9999

    results = run_job(BorgPruneJob, params, emitted)

    assert len(results) == 1
    assert len(emitted['backup_finished']) == 1
    assert results[0]['returncode'] == JOB_EXCEPTION_RETURNCODE
    assert 'DoesNotExist' in results[0]['exception']
    # The final save already recorded what Borg returned.
    assert EventLogModel.get_by_id(results[0]['log_entry_id']).returncode == 0


class RaisesAfterEmitJob(BorgPruneJob):
    def finished_event(self, result):
        self._emit_backup_finished(result)
        self._emit_result(result)
        raise RuntimeError('after the emits')


def test_finished_event_raising_after_its_emits(qapp, profile, mocker, borg_json_output, emitted):
    stdout, stderr = borg_json_output('prune')
    mocker.patch.object(
        vorta.borg.borg_job, 'Popen', return_value=MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    )

    results = run_job(RaisesAfterEmitJob, BorgPruneJob.prepare(profile), emitted)

    assert len(results) == 1
    assert len(emitted['backup_finished']) == 1
    assert results[0]['returncode'] == 0
    assert 'exception' not in results[0]
    assert emitted['progress'][-1].endswith('Task failed: RuntimeError: after the emits')


class RaisesInFinishedEventJob(BorgPruneJob):
    calls = 0

    def finished_event(self, result):
        type(self).calls += 1
        raise RuntimeError('before the emits')


def test_finished_event_is_not_entered_twice(qapp, profile, mocker, borg_json_output, emitted):
    """Create runs the post-backup command in finished_event; a retry would run it a second time."""
    stdout, stderr = borg_json_output('prune')
    mocker.patch.object(
        vorta.borg.borg_job, 'Popen', return_value=MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    )
    RaisesInFinishedEventJob.calls = 0

    results = run_job(RaisesInFinishedEventJob, BorgPruneJob.prepare(profile), emitted)

    assert RaisesInFinishedEventJob.calls == 1
    assert len(results) == 1
    assert len(emitted['backup_finished']) == 1
    assert results[0]['exception'] == 'RuntimeError: before the emits'


def test_process_result_raising(qapp, profile, mocker, borg_json_output, emitted):
    """Rename looks up the archive in process_result. A missing one ends as a failure."""
    stdout, stderr = borg_json_output('rename')
    mocker.patch.object(
        vorta.borg.borg_job, 'Popen', return_value=MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    )
    params = BorgRenameJob.prepare(profile, 'not-in-the-database', 'new-name')

    results = run_job(BorgRenameJob, params, emitted)

    assert len(results) == 1
    assert len(emitted['backup_finished']) == 1
    assert results[0]['returncode'] == JOB_EXCEPTION_RETURNCODE
    assert 'DoesNotExist' in results[0]['exception']
    assert EventLogModel.get_by_id(results[0]['log_entry_id']).returncode == 0


def test_traceback_is_reported_to_the_main_thread(qapp, qtbot, profile, popen_raises, emitted):
    params = BorgPruneJob.prepare(profile)

    with qtbot.waitSignal(qapp.job_exception_event, **pytest._wait_defaults) as blocker:
        run_job(BorgPruneJob, params, emitted)

    assert isinstance(blocker.args[0], str)
    assert 'Traceback' in blocker.args[0]
    assert 'FileNotFoundError' in blocker.args[0]


def test_crashed_check_does_not_open_the_check_dialog(qapp, profile, popen_raises, emitted, mocker):
    message_box = mocker.patch.object(vorta.application, 'QMessageBox')

    results = run_job(BorgCheckJob, BorgCheckJob.prepare(profile), emitted)

    assert len(emitted['check_failed']) == 1
    assert emitted['check_failed'][0] is results[0]
    message_box.assert_not_called()


def test_failure_message_comes_after_success_sounding_text(qapp, profile, popen_raises, emitted):
    run_job(BorgBreakJob, BorgBreakJob.prepare(profile), emitted)

    messages = emitted['progress']
    broken = next(i for i, m in enumerate(messages) if 'Repository lock broken' in m)
    failed = next(i for i, m in enumerate(messages) if 'Task failed: FileNotFoundError' in m)
    assert broken < failed
    assert failed == len(messages) - 1
    assert messages[failed].startswith(f'[{profile.name}] ')


def test_only_one_exception_dialog_at_a_time(qapp, mocker):
    """A dialog opened by the slot blocks in exec(). Reports arriving meanwhile are skipped."""
    shown = []

    def show(exception):
        shown.append(exception)
        qapp._real_job_exception_response('second')  # arrives while the first dialog is open

    mocker.patch.object(vorta.application, 'show_exception_dialog', side_effect=show)

    qapp._real_job_exception_response('first')
    qapp._real_job_exception_response('third')

    assert shown == ['first', 'third']


def _hook_args(exc):
    try:
        raise exc
    except BaseException:
        exc_type, exc_value, exc_tb = sys.exc_info()
    return types.SimpleNamespace(
        exc_type=exc_type, exc_value=exc_value, exc_traceback=exc_tb, thread=threading.current_thread()
    )


def test_thread_exception_hook_logs_critical(qapp, qtbot, caplog):
    with caplog.at_level(logging.CRITICAL):
        with qtbot.waitSignal(qapp.job_exception_event, **pytest._wait_defaults) as blocker:
            thread_exception_hook(_hook_args(RuntimeError('in a thread')))

    records = [r for r in caplog.records if r.levelno == logging.CRITICAL]
    assert len(records) == 1
    assert records[0].exc_info[0] is RuntimeError
    assert 'RuntimeError: in a thread' in blocker.args[0]


def test_thread_exception_hook_ignores_system_exit(qapp, caplog):
    with caplog.at_level(logging.DEBUG):
        thread_exception_hook(_hook_args(SystemExit(0)))

    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]


def test_ui_unblocks_when_a_backup_raises(qapp, qtbot, popen_raises, window_load):
    """The headline case: a backup job that raises must re-enable the Start Backup button."""
    # Load the window only now that no job runs, or it starts with its buttons disabled.
    window_load()
    main = qapp.main_window
    started = threading.Event()
    qapp.backup_started_event.connect(started.set)  # runs after the window disabled its buttons
    try:
        qtbot.waitUntil(lambda: main.createStartBtn.isEnabled(), **pytest._wait_defaults)
        qtbot.mouseClick(main.createStartBtn, QtCore.Qt.MouseButton.LeftButton)
        qtbot.waitUntil(lambda: started.is_set() and main.createStartBtn.isEnabled(), **pytest._wait_defaults)
    finally:
        qapp.backup_started_event.disconnect(started.set)
