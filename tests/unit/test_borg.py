import pytest
import vorta.borg
import vorta.store.models
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
