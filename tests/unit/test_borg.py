import os
import traceback

import pytest

import vorta.application
import vorta.borg
import vorta.store.models
from vorta.borg.borg_job import BorgJob, summarize_traceback
from vorta.borg.prune import BorgPruneJob


def test_borg_prune(qapp, qtbot, mocker, borg_json_output):
    stdout, stderr = borg_json_output('prune')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    params = BorgPruneJob.prepare(vorta.store.models.BackupProfileModel.select().first())
    thread = BorgPruneJob(params['cmd'], params, qapp)

    with qtbot.waitSignal(thread.result, **pytest._wait_defaults) as blocker:
        blocker.connect(thread.updated)
        thread.run()

    assert blocker.args[0]['returncode'] == 0


def test_prepare_bin_does_not_grow_path(monkeypatch):
    """`prepare_bin()` runs for every job, so extending PATH has to be idempotent."""
    monkeypatch.setenv('PATH', '/usr/bin:/bin')
    BorgJob.prepare_bin()
    path_after_first_call = os.environ['PATH']

    for _ in range(3):
        BorgJob.prepare_bin()

    assert os.environ['PATH'] == path_after_first_call
    path_dirs = path_after_first_call.split(os.pathsep)
    assert len(path_dirs) == len(set(path_dirs))


def _traceback_of(func):
    try:
        func()
    except Exception:
        return traceback.format_exc()


def _chained_error():
    try:
        open('/does/not/exist')
    except OSError as e:
        raise RuntimeError('could not open the repository') from e


def test_summarize_traceback():
    sysinfo = 'Platform: Linux host 6.8.0\nBorg: 1.4.4  Python: CPython 3.12.3\nSSH_ORIGINAL_COMMAND: None\n'
    file_error = _traceback_of(lambda: open('/no/such/dir/file'))
    assert file_error.startswith('Traceback (most recent call last):')

    assert summarize_traceback(file_error + '\n' + sysinfo).startswith('FileNotFoundError: [Errno 2]')
    assert summarize_traceback(_traceback_of(_chained_error)) == 'RuntimeError: could not open the repository'

    # Other messages are not changed.
    for message in ['Failed to create/acquire the lock /repo/lock.exclusive (timeout).', '', sysinfo]:
        assert summarize_traceback(message) == message


def test_borg_job_shows_exception_instead_of_traceback(qapp, qtbot, mocker, borg_json_output):
    """Borg logs a traceback after the error. Only its last line is shown and returned as error."""
    mocker.patch.object(vorta.application.QMessageBox, 'show')  # dialog for the LockFailed message
    stdout, stderr = borg_json_output('create_perm')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=2)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)
    log_texts = []

    def record_log(text, context):
        log_texts.append(text)

    qapp.backup_log_event.connect(record_log)

    params = BorgPruneJob.prepare(vorta.store.models.BackupProfileModel.select().first())
    thread = BorgPruneJob(params['cmd'], params, qapp)
    try:
        with qtbot.waitSignal(thread.result, **pytest._wait_defaults) as blocker:
            thread.run()
    finally:
        qapp.backup_log_event.disconnect(record_log)
        if hasattr(qapp, '_msg'):
            del qapp._msg

    exception_line = (
        "borg.locking.LockFailed: Failed to create/acquire the lock /tmp/another/lock.exclusive "
        "([Errno 13] Permission denied: '/tmp/another/lock.exclusive')."
    )
    assert not any('Traceback' in text for text in log_texts)
    assert log_texts[-1].endswith(f'ERROR: {exception_line}')
    assert blocker.args[0]['errors'][-1][1] == exception_line
