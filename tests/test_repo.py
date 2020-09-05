import os
import uuid
from PyQt5 import QtCore
from PyQt5.QtWidgets import QMessageBox

import vorta.borg.borg_thread
import vorta.models
from vorta.views.repo_add_dialog import AddRepoWindow
from vorta.views.ssh_dialog import SSHAddWindow
from vorta.models import EventLogModel, RepoModel, ArchiveModel


def test_repo_add_failures(qapp, qtbot, mocker, borg_json_output):
    # Add new repo window
    main = qapp.main_window
    add_repo_window = AddRepoWindow(main)
    qtbot.addWidget(add_repo_window)

    qtbot.keyClicks(add_repo_window.repoURL, 'aaa')
    qtbot.mouseClick(add_repo_window.saveButton, QtCore.Qt.LeftButton)
    assert add_repo_window.errorText.text().startswith('Please enter a valid')

    qtbot.keyClicks(add_repo_window.repoURL, 'bbb.com:repo')
    qtbot.mouseClick(add_repo_window.saveButton, QtCore.Qt.LeftButton)
    assert add_repo_window.errorText.text() == 'Please use a longer passphrase.'


def test_repo_unlink(qapp, qtbot, monkeypatch):
    monkeypatch.setattr(QMessageBox, "exec_", lambda *args: QMessageBox.Yes)
    main = qapp.main_window
    tab = main.repoTab

    main.tabWidget.setCurrentIndex(0)
    qtbot.mouseClick(tab.repoRemoveToolbutton, QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: tab.repoSelector.count() == 4, timeout=5000)
    assert RepoModel.select().count() == 0

    qtbot.mouseClick(main.createStartBtn, QtCore.Qt.LeftButton)
    assert main.progressText.text() == 'Add a backup repository first.'


def test_repo_add_success(qapp, qtbot, mocker, borg_json_output):
    LONG_PASSWORD = 'long-password-long'

    # Add new repo window
    main = qapp.main_window
    main.repoTab.repo_added.disconnect()
    add_repo_window = AddRepoWindow(main)
    test_repo_url = f'vorta-test-repo.{uuid.uuid4()}.com:repo'  # Random repo URL to avoid macOS keychain

    qtbot.keyClicks(add_repo_window.repoURL, test_repo_url)
    qtbot.keyClicks(add_repo_window.passwordLineEdit, LONG_PASSWORD)

    stdout, stderr = borg_json_output('info')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_thread, 'Popen', return_value=popen_result)

    qtbot.mouseClick(add_repo_window.saveButton, QtCore.Qt.LeftButton)

    with qtbot.waitSignal(add_repo_window.thread.result, timeout=3000) as blocker:
        pass

    main.repoTab.process_new_repo(blocker.args[0])

    assert EventLogModel.select().count() == 1
    assert RepoModel.get(id=2).url == test_repo_url

    from vorta.utils import keyring
    assert keyring.get_password("vorta-repo", RepoModel.get(id=2).url) == LONG_PASSWORD


def test_ssh_dialog(qtbot, tmpdir):
    ssh_dialog = SSHAddWindow()
    ssh_dir = tmpdir
    key_tmpfile = ssh_dir.join("id_rsa-test")
    pub_tmpfile = ssh_dir.join("id_rsa-test.pub")
    key_tmpfile_full = os.path.join(key_tmpfile.dirname, key_tmpfile.basename)
    ssh_dialog.outputFileTextBox.setText(key_tmpfile_full)
    qtbot.mouseClick(ssh_dialog.generateButton, QtCore.Qt.LeftButton)

    qtbot.waitUntil(lambda: key_tmpfile.check(file=1))
    qtbot.waitUntil(lambda: pub_tmpfile.check(file=1))

    key_tmpfile_content = key_tmpfile.read()
    pub_tmpfile_content = pub_tmpfile.read()
    assert key_tmpfile_content.startswith('-----BEGIN OPENSSH PRIVATE KEY-----')
    assert pub_tmpfile_content.startswith('ssh-ed25519')
    qtbot.waitUntil(lambda: ssh_dialog.errors.text().startswith('New key was copied'))

    qtbot.mouseClick(ssh_dialog.generateButton, QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: ssh_dialog.errors.text().startswith('Key file already'))


def test_create(qapp, borg_json_output, mocker, qtbot):
    main = qapp.main_window
    stdout, stderr = borg_json_output('create')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_thread, 'Popen', return_value=popen_result)

    qtbot.mouseClick(main.createStartBtn, QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: main.progressText.text().startswith('Backup finished.'), timeout=3000)
    qtbot.waitUntil(lambda: main.createStartBtn.isEnabled(), timeout=3000)
    assert EventLogModel.select().count() == 1
    assert ArchiveModel.select().count() == 3
    assert RepoModel.get(id=1).unique_size == 15520474
    assert main.createStartBtn.isEnabled()
    assert main.archiveTab.archiveTable.rowCount() == 3
    assert main.scheduleTab.logTableWidget.rowCount() == 1
