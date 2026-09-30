import os

import pytest

import vorta.borg
import vorta.store.models
from vorta.borg.borg_job import BorgJob
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
