import vorta.borg
import vorta.models


def test_scheduler_create_backup(app, qtbot, mocker, borg_json_output):
    stdout, stderr = borg_json_output('create')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_thread, 'Popen', return_value=popen_result)

    app.scheduler.create_backup(1)

    qtbot.waitUntil(lambda: vorta.models.EventLogModel.select().count() == 2, timeout=5000)
