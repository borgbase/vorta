import pytest
import vorta.borg
import vorta.store.models
from vorta.borg.prune import BorgPruneJob


def test_borg_prune(qapp, qtbot):

    params = BorgPruneJob.prepare(vorta.store.models.BackupProfileModel.select().first())
    thread = BorgPruneJob(params['cmd'], params, qapp)

    with qtbot.waitSignal(thread.result, **pytest._wait_defaults) as blocker:
        blocker.connect(thread.updated)
        thread.run()

    assert blocker.args[0]['returncode'] == 0
