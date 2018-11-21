from PyQt5 import QtCore

import vorta.borg.borg_thread
import vorta.models
from vorta.views.repo_add import AddRepoWindow
from vorta.models import EventLogModel, RepoModel, SnapshotModel


def test_create_fail(app, qtbot):
    main = app.main_window
    qtbot.mouseClick(main.createStartBtn, QtCore.Qt.LeftButton)
    assert main.createProgressText.text() == 'Add a backup repository first.'


def test_repo_add(app, qtbot, mocker, borg_json_output):
    # Add new repo window
    main = app.main_window
    add_repo_window = AddRepoWindow(main.repoTab)
    qtbot.keyClicks(add_repo_window.repoURL, 'aaa')
    qtbot.mouseClick(add_repo_window.saveButton, QtCore.Qt.LeftButton)
    assert add_repo_window.errorText.text().startswith('Please enter a valid')

    qtbot.keyClicks(add_repo_window.repoURL, 'bbb.com:repo')
    qtbot.mouseClick(add_repo_window.saveButton, QtCore.Qt.LeftButton)
    assert add_repo_window.errorText.text() == 'Please use a longer password.'

    qtbot.keyClicks(add_repo_window.passwordLineEdit, 'long-password-long')

    stdout, stderr = borg_json_output('info')
    popen_result =mocker.MagicMock(stdout=stdout,
                              stderr=stderr,
                              returncode=0)
    mocker.patch.object(vorta.borg.borg_thread, 'Popen', return_value=popen_result)

    qtbot.mouseClick(add_repo_window.saveButton, QtCore.Qt.LeftButton)

    with qtbot.waitSignal(add_repo_window.thread.result, timeout=1000) as blocker:
        pass

    main.repoTab.process_new_repo(blocker.args[0])

    # assert EventLogModel.select().count() == 2
    assert RepoModel.get(id=1).url == 'aaabbb.com:repo'

def test_create(app_with_repo, borg_json_output, mocker, qtbot):
    main = app_with_repo.main_window
    stdout, stderr = borg_json_output('create')
    popen_result =mocker.MagicMock(stdout=stdout,
                                   stderr=stderr,
                                   returncode=0)
    mocker.patch.object(vorta.borg.borg_thread, 'Popen', return_value=popen_result)

    qtbot.mouseClick(main.createStartBtn, QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: main.createProgressText.text().startswith('Backup finished.'))
    qtbot.waitUntil(lambda: main.createStartBtn.isEnabled())
    assert EventLogModel.select().count() == 1
    assert SnapshotModel.select().count() == 1
    assert RepoModel.get(id=1).unique_size == 15520474
    assert main.createStartBtn.isEnabled()
    assert main.snapshotTab.snapshotTable.rowCount() == 1
    assert main.scheduleTab.logTableWidget.rowCount() == 1

