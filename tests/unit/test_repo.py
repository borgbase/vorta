import os
import uuid

import pytest
import vorta.borg.borg_job
from PyQt6 import QtCore
from PyQt6.QtWidgets import QMessageBox
from vorta.keyring.abc import VortaKeyring
from vorta.store.models import ArchiveModel, EventLogModel, RepoModel

LONG_PASSWORD = 'long-password-long'
SHORT_PASSWORD = 'hunter2'


def test_repo_add_failures(qapp, qtbot, mocker, borg_json_output):
    # Add new repo window
    main = qapp.main_window
    main.repoTab.new_repo()
    add_repo_window = main.repoTab._window
    qtbot.addWidget(add_repo_window)

    qtbot.keyClicks(add_repo_window.passwordInput.passwordLineEdit, LONG_PASSWORD)
    qtbot.keyClicks(add_repo_window.passwordInput.confirmLineEdit, LONG_PASSWORD)
    qtbot.keyClicks(add_repo_window.repoURL, 'aaa')
    qtbot.mouseClick(add_repo_window.saveButton, QtCore.Qt.MouseButton.LeftButton)
    assert add_repo_window.errorText.text().startswith('Please enter a valid')

    add_repo_window.passwordInput.passwordLineEdit.clear()
    add_repo_window.passwordInput.confirmLineEdit.clear()
    qtbot.keyClicks(add_repo_window.passwordInput.passwordLineEdit, SHORT_PASSWORD)
    qtbot.keyClicks(add_repo_window.passwordInput.confirmLineEdit, SHORT_PASSWORD)
    qtbot.keyClicks(add_repo_window.repoURL, 'bbb.com:repo')
    qtbot.mouseClick(add_repo_window.saveButton, QtCore.Qt.MouseButton.LeftButton)
    assert add_repo_window.passwordInput.validation_label.text() == 'Passwords must be atleast 9 characters long.'

    add_repo_window.passwordInput.passwordLineEdit.clear()
    add_repo_window.passwordInput.confirmLineEdit.clear()
    qtbot.keyClicks(add_repo_window.passwordInput.passwordLineEdit, SHORT_PASSWORD + "1")
    qtbot.keyClicks(add_repo_window.passwordInput.confirmLineEdit, SHORT_PASSWORD)
    qtbot.mouseClick(add_repo_window.saveButton, QtCore.Qt.MouseButton.LeftButton)
    assert (
        add_repo_window.passwordInput.validation_label.text()
        == 'Passwords must be identical and atleast 9 characters long.'
    )

    add_repo_window.passwordInput.passwordLineEdit.clear()
    add_repo_window.passwordInput.confirmLineEdit.clear()
    qtbot.keyClicks(add_repo_window.passwordInput.passwordLineEdit, LONG_PASSWORD)
    qtbot.keyClicks(add_repo_window.passwordInput.confirmLineEdit, SHORT_PASSWORD)
    qtbot.mouseClick(add_repo_window.saveButton, QtCore.Qt.MouseButton.LeftButton)
    assert add_repo_window.passwordInput.validation_label.text() == 'Passwords must be identical.'


def test_repo_unlink(qapp, qtbot, monkeypatch):
    main = qapp.main_window
    tab = main.repoTab
    monkeypatch.setattr(QMessageBox, "show", lambda *args: True)

    main.tabWidget.setCurrentIndex(0)
    qtbot.mouseClick(tab.repoRemoveToolbutton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: tab.repoSelector.count() == 1, **pytest._wait_defaults)
    assert RepoModel.select().count() == 0

    qtbot.mouseClick(main.createStartBtn, QtCore.Qt.MouseButton.LeftButton)
    # -1 is the repo id in this test
    qtbot.waitUntil(lambda: 'Select a backup repository first.' in main.progressText.text(), **pytest._wait_defaults)
    assert 'Select a backup repository first.' in main.progressText.text()


def test_password_autofill(qapp, qtbot):
    main = qapp.main_window
    main.repoTab.new_repo()  # couldn't click menu
    add_repo_window = main.repoTab._window
    test_repo_url = f'vorta-test-repo.{uuid.uuid4()}.com:repo'  # Random repo URL to avoid macOS keychain

    keyring = VortaKeyring.get_keyring()
    password = str(uuid.uuid4())
    keyring.set_password('vorta-repo', test_repo_url, password)

    qtbot.keyClicks(add_repo_window.repoURL, test_repo_url)

    assert add_repo_window.passwordInput.passwordLineEdit.text() == password


def test_repo_add_success(qapp, qtbot, mocker, borg_json_output):
    # Add new repo window
    main = qapp.main_window
    main.repoTab.new_repo()  # couldn't click menu
    add_repo_window = main.repoTab._window
    test_repo_url = f'vorta-test-repo.{uuid.uuid4()}.com:repo'  # Random repo URL to avoid macOS keychain
    test_repo_name = 'Test Repo'

    qtbot.keyClicks(add_repo_window.repoURL, test_repo_url)
    qtbot.keyClicks(add_repo_window.repoName, test_repo_name)
    qtbot.keyClicks(add_repo_window.passwordInput.passwordLineEdit, LONG_PASSWORD)
    qtbot.keyClicks(add_repo_window.passwordInput.confirmLineEdit, LONG_PASSWORD)

    stdout, stderr = borg_json_output('info')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    add_repo_window.run()
    qtbot.waitUntil(
        lambda: EventLogModel.select().where(EventLogModel.returncode == 0).count() == 2, **pytest._wait_defaults
    )

    assert RepoModel.get(id=2).url == test_repo_url

    keyring = VortaKeyring.get_keyring()
    assert keyring.get_password("vorta-repo", RepoModel.get(id=2).url) == LONG_PASSWORD
    assert main.repoTab.repoSelector.currentText() == f"{test_repo_name} - {test_repo_url}"


def test_ssh_dialog(qapp, qtbot, tmpdir):
    main = qapp.main_window
    qtbot.mouseClick(main.repoTab.bAddSSHKey, QtCore.Qt.MouseButton.LeftButton)
    ssh_dialog = main.repoTab._window

    ssh_dir = tmpdir
    key_tmpfile = ssh_dir.join("id_rsa-test")
    pub_tmpfile = ssh_dir.join("id_rsa-test.pub")
    key_tmpfile_full = os.path.join(key_tmpfile.dirname, key_tmpfile.basename)
    ssh_dialog.outputFileTextBox.setText(key_tmpfile_full)
    ssh_dialog.generate_key()

    # Ensure new key files exist
    qtbot.waitUntil(lambda: ssh_dialog.errors.text().startswith('New key was copied'), **pytest._wait_defaults)
    assert len(ssh_dir.listdir()) == 2

    # Ensure valid keys were created
    key_tmpfile_content = key_tmpfile.read()
    assert key_tmpfile_content.startswith('-----BEGIN OPENSSH PRIVATE KEY-----')
    pub_tmpfile_content = pub_tmpfile.read()
    assert pub_tmpfile_content.startswith('ssh-ed25519')

    ssh_dialog.generate_key()
    qtbot.waitUntil(lambda: ssh_dialog.errors.text().startswith('Key file already'), **pytest._wait_defaults)


def test_create(qapp, borg_json_output, mocker, qtbot):
    main = qapp.main_window
    stdout, stderr = borg_json_output('create')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    qtbot.mouseClick(main.createStartBtn, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: 'Backup finished.' in main.progressText.text(), **pytest._wait_defaults)
    qtbot.waitUntil(lambda: main.createStartBtn.isEnabled(), **pytest._wait_defaults)
    assert EventLogModel.select().count() == 1
    assert ArchiveModel.select().count() == 3
    assert RepoModel.get(id=1).unique_size == 15520474
    assert main.createStartBtn.isEnabled()
    assert main.archiveTab.archiveTable.rowCount() == 3
    assert main.scheduleTab.logTableWidget.rowCount() == 1
