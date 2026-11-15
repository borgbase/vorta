import sys
import uuid
from unittest.mock import PropertyMock, patch

import pytest


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
def test_keyring_non_ascii_repo():
    from vorta.keyring.darwin import VortaDarwinKeyring

    UNICODE_PW = 'password'
    REPO = 'vorta-test-repo-한글'

    keyring = VortaDarwinKeyring()
    keyring.set_password('vorta-repo', REPO, UNICODE_PW)
    assert keyring.get_password("vorta-repo", REPO) == UNICODE_PW


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
@pytest.mark.parametrize('states, unlock_calls', [([0, 1], 1), ([1, 1], 0), ([0, 0], 1)])
def test_try_unlock_mocked(states, unlock_calls):
    from vorta.keyring.darwin import VortaDarwinKeyring

    keyring = VortaDarwinKeyring()
    keyring.login_keychain = object()
    with (
        patch.object(VortaDarwinKeyring, 'is_unlocked', new_callable=PropertyMock, side_effect=states),
        patch.object(VortaDarwinKeyring, '_set_keychain') as set_keychain,
        patch('vorta.keyring.darwin.SecKeychainUnlock', create=True) as unlock,
    ):
        assert keyring.try_unlock() is bool(states[-1])
        assert unlock.call_count == unlock_calls
        if unlock_calls:
            unlock.assert_called_once_with(keyring.login_keychain, 0, None, False)
        set_keychain.assert_not_called()
