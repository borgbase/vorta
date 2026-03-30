import logging
import os
import uuid
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest
from PyQt6 import QtCore
from PyQt6.QtWidgets import QMessageBox

import vorta.borg.borg_job
from vorta.keyring.abc import VortaKeyring
from vorta.store.models import ArchiveModel, BackupProfileModel, EventLogModel, RepoModel
from vorta.views.dialogs.repo.repo_add import AddRepoWindow

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
    # add new repo window
    main = qapp.main_window
    tab = main.repoTab
    tab.add_repo()
    add_repo_window = tab._window
    qtbot.addWidget(add_repo_window)

    # reveal init only widgets so password validation is active
    add_repo_window._set_init_widgets_visible(True)
    add_repo_window.passwordInput.set_validation_enabled(True)

    qtbot.keyClicks(add_repo_window.passwordInput.passwordLineEdit, first_password)
    qtbot.keyClicks(add_repo_window.passwordInput.confirmLineEdit, second_password)
    add_repo_window.passwordInput.validate()
    assert add_repo_window.passwordInput.validation_label.text() == validation_error


@pytest.mark.parametrize(
    "repo_name, status_text",
    [
        ('test_repo_name', 'Checking repository\u2026'),  # valid repo name, probe starts
        ('a' * 64, 'Checking repository\u2026'),  # also valid (<=64 characters)
        ('a' * 65, 'Repository name must be less than 65 characters.'),  # not valid (>64 characters)
    ],
)
def test_repo_add_name_validation(qapp, qtbot, borg_json_output, repo_name, status_text):
    main = qapp.main_window
    tab = main.repoTab
    tab.add_repo()
    add_repo_window = tab._window
    test_repo_url = f'vorta-test-repo.{uuid.uuid4()}.com:repo'  # Random repo URL to avoid macOS keychain
    qtbot.addWidget(add_repo_window)

    qtbot.keyClicks(add_repo_window.repoURL, test_repo_url)
    qtbot.keyClicks(add_repo_window.repoName, repo_name)
    qtbot.mouseClick(add_repo_window.saveButton, QtCore.Qt.MouseButton.LeftButton)
    assert add_repo_window.errorText.text() == status_text


def test_repo_unlink(qapp, qtbot, monkeypatch):
    main = qapp.main_window
    tab = main.repoTab
    monkeypatch.setattr(QMessageBox, "show", lambda *args: True)

    # Assuming unlink action is the 1st in submenu
    tab.menuRepoUtil.actions()[0].trigger()

    qtbot.waitUntil(lambda: tab.repoSelector.count() == 1, **pytest._wait_defaults)
    assert RepoModel.select().count() == 0

    # Directly call create_backup_action and wait for signal
    with qtbot.waitSignal(qapp.backup_progress_event, timeout=5000):
        qapp.create_backup_action()

    assert 'Select a backup repository first.' in main.progressText.text()


def test_repo_unlink_shared_repository_keeps_dropdown_entry(qapp, qtbot, mocker, monkeypatch):
    main = qapp.main_window
    tab = main.repoTab
    current_profile = main.current_profile
    shared_repo = current_profile.repo
    other_profile = BackupProfileModel.create(name='Shared Repo Profile', repo=shared_repo.id)
    monkeypatch.setattr(QMessageBox, "show", lambda *args: True)

    mock_title = mocker.patch.object(QMessageBox, "setWindowTitle")
    mock_text = mocker.patch.object(QMessageBox, "setText")

    assert tab.repoSelector.count() == 2
    assert tab.repoSelector.currentData() == shared_repo.id

    tab.repo_unlink_action()

    refreshed_profile = BackupProfileModel.get(id=current_profile.id)
    refreshed_other_profile = BackupProfileModel.get(id=other_profile.id)

    assert refreshed_profile.repo is None
    assert refreshed_other_profile.repo.id == shared_repo.id
    assert RepoModel.get_or_none(id=shared_repo.id) is not None
    assert tab.repoSelector.count() == 2
    assert tab.repoSelector.currentData() is None
    assert tab.repoSelector.currentIndex() == 0
    mock_title.assert_called_with('Repository was Detached')
    mock_text.assert_called_with('The repository remains available for other profiles.')


def test_password_autofill(qapp, qtbot):
    main = qapp.main_window
    tab = main.repoTab
    tab.add_repo()
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
    tab.add_repo()
    add_repo_window = tab._window
    qtbot.addWidget(add_repo_window)

    # add repo with invalid URL
    qtbot.keyClicks(add_repo_window.repoURL, 'aaa')
    qtbot.mouseClick(add_repo_window.saveButton, QtCore.Qt.MouseButton.LeftButton)
    assert add_repo_window.errorText.text().startswith('Please enter a valid repo URL')


def test_repo_add_success(qapp, qtbot, mocker, borg_json_output):
    main = qapp.main_window
    tab = main.repoTab
    tab.add_repo()
    add_repo_window = tab._window
    test_repo_url = f'vorta-test-repo.{uuid.uuid4()}.com:repo'  # random repo URL to avoid macOS keychain
    test_repo_name = 'Test Repo'

    # enter valid repo URL, name, and password
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

    # Ensures new key file was created
    qtbot.waitUntil(lambda: ssh_dialog_closed.called, **pytest._wait_defaults)
    assert len(ssh_dir.listdir()) == 2

    # Ensures new key is populated in SSH combobox
    mocker.patch('os.path.expanduser', return_value=str(tmpdir))
    tab.init_ssh()
    assert tab.sshComboBox.count() == 2

    # Ensures valid keys were created
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

    # Ensures no new ney file was created
    assert len(ssh_dir.listdir()) == 0

    # Ensures no new key file in combo box
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
        {"return_code": 130, "error": "", "icon": None, "info": None},
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


def test_repo_change_passphrase_action(qapp, mocker):
    """Test that the ChangeBorgPassphraseWindow is opened and the signal is connected."""
    tab = qapp.main_window.repoTab

    mock_profile = MagicMock()
    mock_profile.repo.encryption = 'repokey-blake2'
    tab.profile = MagicMock(return_value=mock_profile)

    mock_window_cls = mocker.patch('vorta.views.repo_tab.ChangeBorgPassphraseWindow')
    mock_window = mock_window_cls.return_value

    tab.repo_change_passphrase_action()

    mock_window_cls.assert_called_once_with(mock_profile)
    mock_window.setParent.assert_called_once_with(tab, QtCore.Qt.WindowType.Sheet)
    mock_window.open.assert_called_once()
    mock_window.change_borg_passphrase.connect.assert_called_once_with(tab._handle_passphrase_change_result)


@pytest.mark.parametrize(
    "result, expected_title, expected_text",
    [
        (
            {"returncode": 0},
            "Passphrase Changed",
            "The borg passphrase was successfully changed.",
        ),
        (
            {"returncode": 1},
            "Passphrase Change Failed",
            "Unable to change the repository passphrase. Please try again.",
        ),
    ],
)
def test_handle_passphrase_change_result(qapp, qtbot, mocker, result, expected_title, expected_text):
    """Test the _handle_passphrase_change_result method for both success and failure cases."""
    main = qapp.main_window
    tab = main.repoTab

    mock_msgbox = mocker.patch('vorta.views.repo_tab.QMessageBox', autospec=True)
    mock_instance = mock_msgbox.return_value

    tab._handle_passphrase_change_result(result)

    mock_instance.setWindowTitle.assert_called_once_with(tab.tr(expected_title))
    mock_instance.setText.assert_called_once_with(tab.tr(expected_text))
    mock_instance.show.assert_called_once()


@pytest.mark.parametrize(
    "error_message",
    [
        'Repository /tmp/nonexistent-repo does not exist.',
        '/tmp/nonexistent-repo is not a valid repository. Check repo config.',
    ],
)
def test_add_repo_not_found_offers_init(qapp, qtbot, mocker, error_message):
    main = qapp.main_window
    tab = main.repoTab
    tab.add_repo()
    window = tab._window

    mocker.patch.object(
        QMessageBox,
        'question',
        return_value=QMessageBox.StandardButton.Yes,
    )
    mock_init = mocker.patch.object(window, '_init_repo')

    qtbot.keyClicks(window.passwordInput.passwordLineEdit, 'long-password-long')
    qtbot.keyClicks(window.passwordInput.confirmLineEdit, 'long-password-long')
    window.repoURL.setText('/tmp/nonexistent-repo')
    window.repoName.setText('Test Repo')
    window.is_remote_repo = False

    result = {
        'returncode': 2,
        'cmd': ['borg', 'info', '/tmp/nonexistent-repo'],
        'errors': [(logging.ERROR, error_message)],
        'params': {'repo_url': '/tmp/nonexistent-repo', 'profile_name': 'Default'},
        'data': '',
    }
    window._probe_result(result)

    QMessageBox.question.assert_called_once()
    mock_init.assert_called_once()


def test_add_repo_not_found_user_declines(qapp, qtbot, mocker):
    main = qapp.main_window
    tab = main.repoTab
    tab.add_repo()
    window = tab._window

    mocker.patch.object(
        QMessageBox,
        'question',
        return_value=QMessageBox.StandardButton.No,
    )

    window.repoURL.setText('/tmp/nonexistent-repo')
    window.is_remote_repo = False

    result = {
        'returncode': 2,
        'cmd': ['borg', 'info', '/tmp/nonexistent-repo'],
        'errors': [(logging.ERROR, 'Repository /tmp/nonexistent-repo does not exist.')],
        'params': {'repo_url': '/tmp/nonexistent-repo', 'profile_name': 'Default'},
        'data': '',
    }
    window._probe_result(result)

    assert window.errorText.text() == 'Unable to add your repository.'


def test_add_repo_other_error_no_init_offer(qapp, qtbot, mocker):
    main = qapp.main_window
    tab = main.repoTab
    tab.add_repo()
    window = tab._window

    mock_question = mocker.patch.object(QMessageBox, 'question')

    window.repoURL.setText('host.example.com:repo')
    window.is_remote_repo = True

    result = {
        'returncode': 2,
        'cmd': ['borg', 'info', 'host.example.com:repo'],
        'errors': [(logging.ERROR, 'Connection refused')],
        'params': {'repo_url': 'host.example.com:repo', 'profile_name': 'Default'},
        'data': '',
    }
    window._probe_result(result)

    mock_question.assert_not_called()
    assert window.errorText.text() == 'Connection refused'


def test_add_repo_probe_succeeds_connects(qapp, qtbot):
    window = AddRepoWindow()

    signal_received = []
    window.added_repo.connect(lambda r: signal_received.append(r))

    result = {
        'returncode': 0,
        'cmd': ['borg', 'info', '/tmp/existing-repo'],
        'errors': [],
        'params': {'repo_url': '/tmp/existing-repo', 'repo_name': 'Test'},
        'data': {},
    }
    window._probe_result(result)

    assert len(signal_received) == 1
    assert signal_received[0]['returncode'] == 0
