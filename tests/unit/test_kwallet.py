from unittest.mock import patch

import pytest
from PyQt6.QtCore import QVariant

from vorta.keyring.kwallet import KWalletNotAvailableException, VortaKWallet5Keyring


@pytest.fixture
def kwallet_keyring():
    with patch('vorta.keyring.kwallet.QtDBus.QDBusInterface') as MockInterface:
        mock_iface = MockInterface.return_value
        mock_iface.isValid.return_value = True

        with patch.object(VortaKWallet5Keyring, 'get_result') as mock_get_result:
            mock_get_result.side_effect = lambda method, args=[]: (True if method == "isEnabled" else None)

            mock_iface.callWithArgumentList.return_value.arguments.return_value = [1]
            yield VortaKWallet5Keyring()


@patch('vorta.keyring.kwallet.QtDBus.QDBusInterface')
def test_init_valid(mock_iface):
    mock_iface.return_value.isValid.return_value = True
    with patch.object(VortaKWallet5Keyring, 'get_result', return_value=True):
        keyring = VortaKWallet5Keyring()
        assert keyring.iface.isValid()


@patch('vorta.keyring.kwallet.QtDBus.QDBusInterface')
def test_init_invalid(mock_iface):
    mock_iface.return_value.isValid.return_value = False

    with pytest.raises(KWalletNotAvailableException):
        VortaKWallet5Keyring()


def test_set_password(kwallet_keyring):
    with patch.object(kwallet_keyring, 'get_result', return_value=None) as mock_get_result:
        kwallet_keyring.set_password('test_service', 'test_repo', 'test_password')
        mock_get_result.assert_called_once_with(
            "writePassword",
            args=[kwallet_keyring.handle, kwallet_keyring.folder_name, 'test_repo', 'test_password', 'test_service'],
        )


def test_get_password(kwallet_keyring):
    wId = QVariant(0)

    with patch.object(kwallet_keyring, 'get_result') as mock_get_result:
        mock_get_result.side_effect = [
            'test_wallet',  # networkWallet
            42,  # open (wallet handle)
            True,  # hasEntry
            'test_password',  # readPassword
        ]

        password = kwallet_keyring.get_password('test_service', 'test_repo')

        # Debug assertions to ensure proper flow
        mock_get_result.assert_any_call("networkWallet")
        mock_get_result.assert_any_call("open", args=['test_wallet', wId, 'vorta-repo'])
        mock_get_result.assert_any_call(
            "hasEntry", args=[kwallet_keyring.handle, kwallet_keyring.folder_name, 'test_repo', 'test_service']
        )
        mock_get_result.assert_any_call(
            "readPassword", args=[kwallet_keyring.handle, kwallet_keyring.folder_name, 'test_repo', 'test_service']
        )

        assert password == 'test_password'


def test_get_password_not_found(kwallet_keyring):
    kwallet_keyring.iface.callWithArgumentList.return_value.arguments.return_value = [False]

    password = kwallet_keyring.get_password('test_service', 'test_repo')
    assert password is None


def test_try_unlock(kwallet_keyring):
    kwallet_keyring.iface.call.return_value.arguments.return_value = ['test_wallet']
    kwallet_keyring.iface.callWithArgumentList.return_value.arguments.return_value = [42]

    kwallet_keyring.try_unlock()
    assert kwallet_keyring.handle > 0
