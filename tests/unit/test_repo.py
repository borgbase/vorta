import os
import uuid
from typing import Any, Dict

import pytest
import vorta.borg.borg_job
from PyQt6 import QtCore
from PyQt6.QtWidgets import QMessageBox
from vorta.keyring.abc import VortaKeyring
from vorta.store.models import ArchiveModel, EventLogModel, RepoModel

LONG_PASSWORD = 'long-password-long'
SHORT_PASSWORD = 'hunter2'


@pytest.mark.parametrize(
    "first_password, second_password, validation_error",
    [
        (SHORT_PASSWORD, SHORT_PASSWORD, 'Passwords must be at least 9 characters long.'),
        (LONG_PASSWORD, SHORT_PASSWORD, 'Passwords must be identical.'),
        (SHORT_PASSWORD + "1", SHORT_PASSWORD, 'Passwords must be identical and at least 9 characters long.'),
        (LONG_PASSWORD, LONG_PASSWORD, ''),  # no error, password meets requirements.
    ],
)
def test_new_repo_password_validation(qapp, qtbot, borg_json_output, first_password, second_password, validation_error):
    # Add new repo window
    main = qapp.main_window
    tab = main.repoTab
    tab.new_repo()
    add_repo_window = tab._window
    qtbot.addWidget(add_repo_window)

    qtbot.keyClicks(add_repo_window.passwordInput.passwordLineEdit, first_password)
    qtbot.keyClicks(add_repo_window.passwordInput.confirmLineEdit, second_password)
    qtbot.mouseClick(add_repo_window.saveButton, QtCore.Qt.MouseButton.LeftButton)
    assert add_repo_window.passwordInput.validation_label.text() == validation_error


@pytest.mark.parametrize(
    "repo_name, error_text",
    [
        ('test_repo_name', ''),  # valid repo name
        ('a' * 64, ''),  # also valid (<=64 characters)
        ('a' * 65, 'Repository name must be less than 65 characters.'),  # not valid (>64 characters)
    ],
)
def test_repo_add_name_validation(qapp, qtbot, borg_json_output, repo_name, error_text):
    main = qapp.main_window
    tab = main.repoTab
    tab.new_repo()
    add_repo_window = tab._window
    test_repo_url = f'vorta-test-repo.{uuid.uuid4()}.com:repo'  # Random repo URL to avoid macOS keychain
    qtbot.addWidget(add_repo_window)

    qtbot.keyClicks(add_repo_window.repoURL, test_repo_url)
    qtbot.keyClicks(add_repo_window.repoName, repo_name)
    qtbot.mouseClick(add_repo_window.saveButton, QtCore.Qt.MouseButton.LeftButton)
    assert add_repo_window.errorText.text() == error_text


def test_repo_unlink(qapp, qtbot, monkeypatch):
    main = qapp.main_window
    tab = main.repoTab
    monkeypatch.setattr(QMessageBox, "show", lambda *args: True)

    qtbot.mouseClick(tab.repoRemoveToolbutton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: tab.repoSelector.count() == 1, **pytest._wait_defaults)
    assert RepoModel.select().count() == 0

    qtbot.mouseClick(main.createStartBtn, QtCore.Qt.MouseButton.LeftButton)
    # -1 is the repo id in this test
    qtbot.waitUntil(lambda: 'Select a backup repository first.' in main.progressText.text(), **pytest._wait_defaults)
    assert 'Select a backup repository first.' in main.progressText.text()


def test_password_autofill(qapp, qtbot):
    main = qapp.main_window
    tab = main.repoTab
    tab.new_repo()
    add_repo_window = tab._window
    test_repo_url = f'vorta-test-repo.{uuid.uuid4()}.com:repo'  # Random repo URL to avoid macOS keychain

    keyring = VortaKeyring.get_keyring()
    password = str(uuid.uuid4())
    keyring.set_password('vorta-repo', test_repo_url, password)

    qtbot.keyClicks(add_repo_window.repoURL, test_repo_url)

    assert add_repo_window.passwordInput.passwordLineEdit.text() == password


def test_repo_add_failure(qapp, qtbot, borg_json_output):
    main = qapp.main_window
    tab = main.repoTab
    tab.new_repo()
    add_repo_window = tab._window
    qtbot.addWidget(add_repo_window)

    # Add repo with invalid URL
    qtbot.keyClicks(add_repo_window.repoURL, 'aaa')
    qtbot.mouseClick(add_repo_window.saveButton, QtCore.Qt.MouseButton.LeftButton)
    assert add_repo_window.errorText.text().startswith('Please enter a valid repo URL')


def test_repo_add_success(qapp, qtbot, mocker, borg_json_output):
    main = qapp.main_window
    tab = main.repoTab
    tab.new_repo()
    add_repo_window = tab._window
    test_repo_url = f'vorta-test-repo.{uuid.uuid4()}.com:repo'  # Random repo URL to avoid macOS keychain
    test_repo_name = 'Test Repo'

    # Enter valid repo URL, name, and password
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
    assert tab.repoSelector.currentText() == f"{test_repo_name} - {test_repo_url}"


def test_ssh_dialog_success(qapp, qtbot, mocker, tmpdir):
    main = qapp.main_window
    tab = main.repoTab

    qtbot.mouseClick(tab.bAddSSHKey, QtCore.Qt.MouseButton.LeftButton)
    ssh_dialog = tab._window
    ssh_dialog_closed = mocker.spy(ssh_dialog, 'reject')
    ssh_dir = tmpdir
    key_tmpfile = ssh_dir.join("id_rsa-test")
    pub_tmpfile = ssh_dir.join("id_rsa-test.pub")
    key_tmpfile_full = os.path.join(key_tmpfile.dirname, key_tmpfile.basename)
    ssh_dialog.outputFileTextBox.setText(key_tmpfile_full)
    ssh_dialog.generate_key()

    # Ensure new key file was created
    qtbot.waitUntil(lambda: ssh_dialog_closed.called, **pytest._wait_defaults)
    assert len(ssh_dir.listdir()) == 2

    # Ensure new key is populated in SSH combobox
    mocker.patch('os.path.expanduser', return_value=str(tmpdir))
    tab.init_ssh()
    assert tab.sshComboBox.count() == 2

    # Ensure valid keys were created
    key_tmpfile_content = key_tmpfile.read()
    assert key_tmpfile_content.startswith('-----BEGIN OPENSSH PRIVATE KEY-----')
    pub_tmpfile_content = pub_tmpfile.read()
    assert pub_tmpfile_content.startswith('ssh-ed25519')


def test_ssh_dialog_failure(qapp, qtbot, mocker, monkeypatch, tmpdir):
    main = qapp.main_window
    tab = main.repoTab
    monkeypatch.setattr(QMessageBox, "show", lambda *args: True)
    failure_message = mocker.spy(tab, "create_ssh_key_failure")

    qtbot.mouseClick(tab.bAddSSHKey, QtCore.Qt.MouseButton.LeftButton)
    ssh_dialog = tab._window
    ssh_dir = tmpdir
    key_tmpfile = ssh_dir.join("invalid///===for_testing")
    key_tmpfile_full = os.path.join(key_tmpfile.dirname, key_tmpfile.basename)
    ssh_dialog.outputFileTextBox.setText(key_tmpfile_full)
    ssh_dialog.generate_key()

    qtbot.waitUntil(lambda: failure_message.called, **pytest._wait_defaults)
    failure_message.assert_called_once()

    # Ensure no new ney file was created
    assert len(ssh_dir.listdir()) == 0

    # Ensure no new key file in combo box
    mocker.patch('os.path.expanduser', return_value=str(tmpdir))
    tab.init_ssh()
    assert tab.sshComboBox.count() == 1


def test_ssh_copy_to_clipboard_action(qapp, qtbot, mocker, tmpdir):
    """Testing the proper QMessageBox dialogue appears depending on the copy action circumstances."""
    tab = qapp.main_window.repoTab

    # set mocks to test assertions and prevent test interruptions
    text = mocker.patch.object(QMessageBox, "setText")
    mocker.patch.object(QMessageBox, "show")
    mocker.patch.object(qapp.clipboard(), "setText")

    qtbot.mouseClick(tab.bAddSSHKey, QtCore.Qt.MouseButton.LeftButton)
    ssh_dialog = tab._window
    ssh_dialog_closed = mocker.spy(ssh_dialog, 'reject')
    ssh_dir = tmpdir
    key_tmpfile = ssh_dir.join("id_rsa-test")
    pub_tmpfile = ssh_dir.join("id_rsa-test.pub")
    key_tmpfile_full = os.path.join(key_tmpfile.dirname, key_tmpfile.basename)
    ssh_dialog.outputFileTextBox.setText(key_tmpfile_full)
    ssh_dialog.generate_key()

    # Ensure new key file was created
    qtbot.waitUntil(lambda: ssh_dialog_closed.called, **pytest._wait_defaults)
    assert len(ssh_dir.listdir()) == 2
    # populate the ssh combobox with the ssh key we created in tmpdir
    mock_expanduser = mocker.patch('os.path.expanduser', return_value=str(tmpdir))
    tab.init_ssh()
    assert tab.sshComboBox.count() == 2

    # test when no ssh key is selected to copy
    assert tab.sshComboBox.currentIndex() == 0
    qtbot.mouseClick(tab.sshKeyToClipboardButton, QtCore.Qt.MouseButton.LeftButton)
    message = "Select a public key from the dropdown first."
    text.assert_called_with(message)

    # Select a key and copy it
    mock_expanduser.return_value = pub_tmpfile
    tab.sshComboBox.setCurrentIndex(1)
    assert tab.sshComboBox.currentIndex() == 1
    qtbot.mouseClick(tab.sshKeyToClipboardButton, QtCore.Qt.MouseButton.LeftButton)
    message = "The selected public SSH key was copied to the clipboard. Use it to set up remote repo permissions."
    text.assert_called_with(message)

    # handle ssh key file not found
    mock_expanduser.return_value = "foobar"
    assert tab.sshComboBox.currentIndex() == 1
    qtbot.mouseClick(tab.sshKeyToClipboardButton, QtCore.Qt.MouseButton.LeftButton)
    message = "Could not find public key."
    text.assert_called_with(message)


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
    assert main.scheduleTab.logPage.logPage.rowCount() == 1


@pytest.mark.parametrize(
    "response",
    [
        {
            "return_code": 0,  # no error
            "error": "",
            "icon": None,
            "info": None,
        },
        {
            "return_code": 1,  # warning
            "error": "Borg exited with warning status (rc 1).",
            "icon": QMessageBox.Icon.Warning,
            "info": "",
        },
        {
            "return_code": 2,  # critical error
            "error": "Repository data check for repo test_repo_url failed. Error code 2",
            "icon": QMessageBox.Icon.Critical,
            "info": "Consider repairing or recreating the repository soon to avoid missing data.",
        },
        {
            "return_code": 135,  # 128 + n = kill signal n
            "error": "killed by signal 7",
            "icon": QMessageBox.Icon.Critical,
            "info": "The process running the check job got a kill signal. Try again.",
        },
        {"return_code": 130, "error": "", "icon": None, "info": None},  # keyboard interrupt
    ],
)
def test_repo_check_failed_response(qapp, qtbot, mocker, response):
    """Test the processing of the signal that a repo consistency check has failed."""
    mock_result: Dict[str, Any] = {
        'params': {'repo_url': 'test_repo_url'},
        'returncode': response["return_code"],
        'errors': [(0, 'test_error_message')] if response["return_code"] not in [0, 130] else None,
    }

    mock_exec = mocker.patch.object(QMessageBox, "exec")
    mock_text = mocker.patch.object(QMessageBox, "setText")
    mock_info = mocker.patch.object(QMessageBox, "setInformativeText")
    mock_icon = mocker.patch.object(QMessageBox, "setIcon")

    qapp.check_failed_response(mock_result)

    # return codes 0 and 130 do not provide a message
    # for all other return codes, assert the message is formatted correctly
    if mock_exec.call_count != 0:
        mock_icon.assert_called_with(response["icon"])
        assert response["error"] in mock_text.call_args[0][0]
        assert response["info"] in mock_info.call_args[0][0]
