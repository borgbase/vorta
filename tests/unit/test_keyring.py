"""BorgJob.prepare unlocks the keyring at most once and only when the repo needs a passphrase (#2606)."""

from unittest.mock import MagicMock

import pytest

from vorta.borg.info_repo import BorgInfoRepoJob
from vorta.borg.prune import BorgPruneJob
from vorta.keyring.abc import VortaKeyring
from vorta.store.models import BackupProfileModel


@pytest.fixture
def keyring(mocker):
    keyring = MagicMock(is_system=False, is_unlocked=False)
    keyring.get_password.return_value = None
    mocker.patch.object(VortaKeyring, 'get_keyring', return_value=keyring)
    return keyring


def profile_with_encryption(encryption):
    profile = BackupProfileModel.select().first()
    profile.repo.encryption = encryption
    profile.repo.save()
    return profile


def test_prepare_unlock_fails(keyring):
    keyring.try_unlock.return_value = False

    ret = BorgPruneJob.prepare(profile_with_encryption('repokey-blake2'))

    assert ret['ok'] is False
    assert ret['message'].startswith('Please unlock')
    keyring.try_unlock.assert_called_once()
    keyring.get_password.assert_not_called()


def test_prepare_unlock_succeeds(keyring):
    keyring.try_unlock.return_value = True
    keyring.get_password.return_value = 'pw'

    ret = BorgPruneJob.prepare(profile_with_encryption('repokey-blake2'))

    assert ret['ok'] is True
    assert ret['password'] == 'pw'
    keyring.try_unlock.assert_called_once()


def test_prepare_unencrypted_repo_locked_keyring(keyring):
    ret = BorgPruneJob.prepare(profile_with_encryption('none'))

    assert ret['ok'] is True
    assert ret['password'] is None
    keyring.try_unlock.assert_not_called()
    keyring.get_password.assert_not_called()


def test_prepare_unencrypted_repo_unlocked_keyring(keyring):
    keyring.is_unlocked = True
    keyring.get_password.return_value = 'pw'

    ret = BorgPruneJob.prepare(profile_with_encryption('none'))

    assert ret['ok'] is True
    assert ret['password'] == 'pw'
    keyring.try_unlock.assert_not_called()


INFO_PARAMS = {'repo_url': 'host.example.com:repo', 'repo_name': 'repo', 'extra_borg_arguments': '', 'ssh_key': None}


def test_info_repo_prepare_unlocks_for_typed_password(keyring):
    keyring.try_unlock.return_value = False

    ret = BorgInfoRepoJob.prepare({**INFO_PARAMS, 'password': 'pw'})

    assert ret['ok'] is False
    assert ret['message'] == 'Please unlock your password manager.'
    keyring.try_unlock.assert_called_once()
    keyring.get_password.assert_not_called()


def test_info_repo_prepare_no_password_still_unlocks(keyring):
    ret = BorgInfoRepoJob.prepare({**INFO_PARAMS, 'password': ''})

    assert ret['ok'] is True
    assert ret['password'] == ''
    keyring.try_unlock.assert_called_once()


def test_info_repo_prepare_no_password_unlock_dismissed(keyring):
    """A repo without passphrase can be added while the keyring stays locked."""
    keyring.try_unlock.return_value = False

    ret = BorgInfoRepoJob.prepare({**INFO_PARAMS, 'password': ''})

    assert ret['ok'] is True
    keyring.try_unlock.assert_called_once()


def test_info_repo_empty_passphrase_kwallet_closed(qapp, mocker):
    """Adding an encrypted repo with an empty passphrase stores it with an open wallet handle."""
    from vorta.keyring.kwallet import VortaKWallet5Keyring

    calls = []
    replies = {'isEnabled': True, 'networkWallet': 'kdewallet', 'isOpen': False, 'open': 7, 'writePassword': 0}

    def get_result(self, method, args=[]):
        calls.append((method, list(args)))
        return replies.get(method)

    mocker.patch('vorta.keyring.kwallet.QtDBus.QDBusInterface').return_value.isValid.return_value = True
    mocker.patch.object(VortaKWallet5Keyring, 'get_result', get_result)
    mocker.patch.object(VortaKeyring, 'get_keyring', side_effect=VortaKWallet5Keyring)

    params = BorgInfoRepoJob.prepare({**INFO_PARAMS, 'password': ''})
    assert params['ok'] is True
    job = BorgInfoRepoJob(params['cmd'], params)
    job.process_result({'returncode': 0, 'params': params, 'data': {'encryption': {'mode': 'repokey'}}})

    writes = [args for method, args in calls if method == 'writePassword']
    assert [args[0] for args in writes] == [7]
    assert [method for method, _ in calls].count('open') == 1
