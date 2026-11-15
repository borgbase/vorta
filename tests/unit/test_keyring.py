"""BorgJob.prepare unlocks the keyring at most once and only when the repo needs a passphrase (#2606)."""

from unittest.mock import MagicMock

import pytest

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
