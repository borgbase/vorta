import pytest
import vorta.borg
from vorta.models import EventLogModel


def test_scheduler_create_backup(qapp, qtbot, mocker, borg_json_output):
    events_before = EventLogModel.select().count()
    stdout, stderr = borg_json_output('create')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    with qtbot.waitSignal(qapp.backup_finished_event, **pytest._wait_defaults):
        qapp.scheduler.create_backup(1)

    assert EventLogModel.select().where(EventLogModel.returncode == 0).count() == events_before + 1
