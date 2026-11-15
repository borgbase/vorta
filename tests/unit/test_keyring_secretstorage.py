from unittest.mock import MagicMock

import pytest

pytest.importorskip('secretstorage')

from vorta.keyring.secretstorage import VortaSecretStorageKeyring  # noqa: E402


@pytest.fixture
def keyring():
    keyring = VortaSecretStorageKeyring.__new__(VortaSecretStorageKeyring)
    keyring.collection = MagicMock()
    return keyring


def test_is_unlocked_does_not_prompt(keyring):
    keyring.collection.is_locked.return_value = True

    assert keyring.is_unlocked is False
    keyring.collection.unlock.assert_not_called()


def test_try_unlock_stays_locked(keyring):
    keyring.collection.is_locked.return_value = True

    assert keyring.try_unlock() is False
    keyring.collection.unlock.assert_called_once()


def test_try_unlock_succeeds(keyring):
    keyring.collection.is_locked.side_effect = [True, False]

    assert keyring.try_unlock() is True
    keyring.collection.unlock.assert_called_once()


def test_try_unlock_already_unlocked(keyring):
    keyring.collection.is_locked.return_value = False

    assert keyring.try_unlock() is True
    keyring.collection.unlock.assert_not_called()


def test_get_password_locked(keyring):
    keyring.collection.is_locked.return_value = True

    assert keyring.get_password('vorta-repo', 'repo') is None
    keyring.collection.search_items.assert_not_called()
