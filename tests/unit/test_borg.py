import os
import traceback

import pytest

import vorta.application
import vorta.borg
import vorta.store.models
from vorta.borg.borg_job import BorgJob, LineOrientedJsonBorgJob, summarize_traceback
from vorta.borg.compact import BorgCompactJob
from vorta.borg.delete import BorgDeleteJob
from vorta.borg.prune import BorgPruneJob
from vorta.store.models import BackupProfileModel, RepoModel, db_lock


@pytest.mark.parametrize('job_class', [BorgPruneJob, BorgDeleteJob])
@pytest.mark.parametrize('outcome', [0, 1, 2, 'exception'])
def test_repo_stats_reset_under_lock_before_finished(qapp, mocker, borg_json_output, job_class, outcome):
    """Even a failed prune/delete can change the repo; clear stats before notifying the UI."""
    profile = BackupProfileModel.get()
    repo = profile.repo
    fields = ('total_size', 'unique_csize', 'unique_size', 'total_unique_chunks')
    for field in fields:
        setattr(repo, field, 100)
    repo.save()
    save = RepoModel.save
    lock_states = []

    def save_repo(repo, *args, **kwargs):
        lock_states.append(db_lock.locked())
        return save(repo, *args, **kwargs)

    mocker.patch.object(RepoModel, 'save', autospec=True, side_effect=save_repo)
    stdout, stderr = borg_json_output('prune')
    process = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=outcome)
    if outcome == 'exception':
        mocker.patch.object(vorta.borg.borg_job, 'Popen', side_effect=OSError('Cannot start Borg'))
    else:
        mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=process)
    params = job_class.prepare(profile, ['test-archive']) if job_class is BorgDeleteJob else job_class.prepare(profile)
    job = job_class(params['cmd'], params, repo.id)
    process_result = mocker.spy(job, 'process_result')
    stats_at_finish = []

    def record_stats(result):
        saved_repo = RepoModel.get_by_id(repo.id)
        stats_at_finish.append([getattr(saved_repo, field) for field in fields])

    qapp.backup_finished_event.connect(record_stats)
    try:
        job.run()
    finally:
        qapp.backup_finished_event.disconnect(record_stats)

    assert lock_states == [True]
    assert stats_at_finish == [[None] * len(fields)]
    process_result.assert_called_once()


def test_compact_start_message(qapp, qtbot, monkeypatch):
    """Keep the profile prefix separate from the translated status message."""
    monkeypatch.setattr(vorta.utils.borg_compat, 'version', '1.2.4')
    params = BorgCompactJob.prepare(BackupProfileModel.get())
    job = BorgCompactJob(params['cmd'], params)

    with qtbot.waitSignal(qapp.backup_progress_event) as signal:
        job.started_event()

    assert signal.args == [f"[{params['profile_name']}] Starting repository compaction..."]


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


def test_line_oriented_json_borg_job_emits_complete_objects(qapp, monkeypatch):
    monkeypatch.setattr(LineOrientedJsonBorgJob, 'prepare_bin', classmethod(lambda cls: 'borg'))
    job = LineOrientedJsonBorgJob(['borg', 'list'], {})
    received = []
    job.objReceived.connect(received.extend)

    job.process_intermediate('{"path":"first"}\n{"path":"sec', True)
    assert received == [{'path': 'first'}]

    job.process_intermediate('', True)
    assert received == [{'path': 'first'}]

    job.process_intermediate('ond"}\n{"path":"third"}\n{"path":"last"}', True)
    assert received == [{'path': 'first'}, {'path': 'second'}, {'path': 'third'}]

    job.process_intermediate('', False)
    assert received == [{'path': 'first'}, {'path': 'second'}, {'path': 'third'}, {'path': 'last'}]


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
