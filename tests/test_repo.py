import io
from PyQt5 import QtCore

import vorta.borg.borg_thread
import vorta.models
from vorta.views.repo_add import AddRepoWindow
from vorta.models import EventLogModel, RepoModel

from .fixtures import *

def test_repo_tab(app, qtbot):
    main = app.main_window
    qtbot.mouseClick(main.createStartBtn, QtCore.Qt.LeftButton)
    assert main.createProgressText.text() == 'Add a remote backup repository first.'


def test_repo_add(app, qtbot, mocker):
    # Add new repo window
    main = app.main_window
    add_repo_window = AddRepoWindow(main.repoTab)
    qtbot.keyClicks(add_repo_window.repoURL, 'aaa')
    qtbot.mouseClick(add_repo_window.saveButton, QtCore.Qt.LeftButton)
    assert add_repo_window.errorText.text() == 'Please enter a valid repo URL including hostname and path.'

    qtbot.keyClicks(add_repo_window.repoURL, 'bbb.com:repo')
    qtbot.mouseClick(add_repo_window.saveButton, QtCore.Qt.LeftButton)
    assert add_repo_window.errorText.text() == 'Please use a longer password.'

    qtbot.keyClicks(add_repo_window.passwordLineEdit, 'long-password-long')

    popen_result =mocker.MagicMock(stdout=io.StringIO("some initial binary data"),
                              stderr=io.StringIO("some initial binary data"),
                              returncode=0)
    mocker.patch.object(vorta.borg.borg_thread, 'Popen', return_value=popen_result)

    qtbot.mouseClick(add_repo_window.saveButton, QtCore.Qt.LeftButton)

    with qtbot.waitSignal(add_repo_window.thread.result, timeout=1000) as blocker:
        pass

    main.repoTab.process_new_repo(blocker.args[0])

    assert EventLogModel.select().count() == 1
    assert RepoModel.get(id=1).url == 'aaabbb.com:repo'

