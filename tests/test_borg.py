import vorta.borg
import vorta.models
from vorta.borg.prune import BorgPruneThread

def test_borg_prune(app, qtbot, mocker, borg_json_output):
    stdout, stderr = borg_json_output('prune')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_thread, 'Popen', return_value=popen_result)

    params = BorgPruneThread.prepare(vorta.models.BackupProfileModel.select().first())
    thread = BorgPruneThread(params['cmd'], params, app)

    with qtbot.waitSignal(thread.result, timeout=10000) as blocker:
        blocker.connect(thread.updated)
        thread.run()

    assert blocker.args[0]['returncode'] == 0
