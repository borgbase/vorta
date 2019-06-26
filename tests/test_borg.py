import os
import vorta.borg
import vorta.models
from vorta.borg.borg_thread import BorgThread
from vorta.borg.info import BorgInfoThread
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


def test_borg_passcommand(app, monkeypatch):
    dummy_borg_passcommand = 'true'

    with monkeypatch.context() as m:
        m.setattr(os, 'environ', {'BORG_PASSCOMMAND': dummy_borg_passcommand})
        params = BorgThread.prepare(vorta.models.BackupProfileModel.select().first())
        thread = BorgThread(['true'], params, app)

        assert thread.env['BORG_PASSCOMMAND'] == dummy_borg_passcommand
        assert 'BORG_PASSPHRASE' not in thread.env


def test_borg_passcommand_info(app, monkeypatch):
    dummy_borg_passcommand = 'true'

    with monkeypatch.context() as m:
        m.setattr(os, 'environ', {'BORG_PASSCOMMAND': dummy_borg_passcommand})
        params = BorgInfoThread.prepare({'ssh_key': '', 'repo_url': '', 'password': '', 'extra_borg_arguments': ''})
        thread = BorgInfoThread(params['cmd'], params)

        assert thread.env['BORG_PASSCOMMAND'] == dummy_borg_passcommand
        assert 'BORG_PASSPHRASE' not in thread.env
