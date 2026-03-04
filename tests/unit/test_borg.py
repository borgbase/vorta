import time

import pytest

import vorta.borg
import vorta.store.models
from vorta.borg.prune import BorgPruneJob


def wait_successful():
    time.sleep(0.1)
    return 0


def test_borg_prune(qapp, qtbot, mocker, borg_json_output):
    stdout, stderr = borg_json_output('prune')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, wait=wait_successful)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    params = BorgPruneJob.prepare(vorta.store.models.BackupProfileModel.select().first())
    thread = BorgPruneJob(params['cmd'], params, qapp)

    with qtbot.waitSignal(thread.result, **pytest._wait_defaults) as blocker:
        blocker.connect(thread.updated)
        thread.run()

    assert blocker.args[0]['returncode'] == 0
