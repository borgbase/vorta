import io
import pytest
from PyQt5 import QtCore

from vorta.models import BackupProfileModel, SnapshotModel
import vorta.borg


def test_prune_intervals(app, qtbot):
    prune_intervals = ['hour', 'day', 'week', 'month', 'year']
    main = app.main_window
    tab = main.snapshotTab
    profile = BackupProfileModel.get(id=1)

    for i in prune_intervals:
        getattr(tab, f'prune_{i}').setValue(9)
        tab.save_prune_setting(None)
        profile = profile.refresh()
        assert getattr(profile, f'prune_{i}') == 9


def test_repo_list(app_with_repo, qtbot, mocker, borg_json_output):
    main = app_with_repo.main_window
    tab = main.snapshotTab
    main.tabWidget.setCurrentIndex(3)
    tab.list_action()
    assert not tab.checkButton.isEnabled()

    stdout, stderr = borg_json_output('list')
    popen_result =mocker.MagicMock(stdout=stdout,
                                   stderr=stderr,
                                   returncode=0)
    mocker.patch.object(vorta.borg.borg_thread, 'Popen', return_value=popen_result)

    with qtbot.waitSignal(app_with_repo.backup_finished_event, timeout=3000) as blocker:
        pass

    assert SnapshotModel.select().count() == 6
    assert main.createProgressText.text() == 'Refreshing snapshots done.'
    assert tab.checkButton.isEnabled()

