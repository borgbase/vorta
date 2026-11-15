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


@patch('vorta.keyring.kwallet.QInputDialog.getText', return_value=('', False))
def test_get_password(mock_dialog, kwallet_keyring):
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


@patch('vorta.keyring.kwallet.QInputDialog.getText', return_value=('', False))
def test_get_password_not_found(mock_dialog, kwallet_keyring):
    kwallet_keyring.iface.callWithArgumentList.return_value.arguments.return_value = [False]

    password = kwallet_keyring.get_password('test_service', 'test_repo')
    assert password is None


@patch('vorta.keyring.kwallet.QInputDialog.getText', return_value=('', False))
def test_try_unlock(mock_dialog, kwallet_keyring):
    with patch.object(kwallet_keyring, 'get_result') as mock_get_result:
        mock_get_result.side_effect = [
            'test_wallet',  # networkWallet
            42,  # open (wallet handle)
        ]
        kwallet_keyring.try_unlock()
        assert kwallet_keyring.handle == 42


@patch('vorta.keyring.kwallet.QInputDialog.getText', return_value=('', False))
def test_is_unlocked_closed_wallet(mock_dialog, kwallet_keyring):
    with patch.object(kwallet_keyring, 'get_result') as mock_get_result:
        mock_get_result.side_effect = ['test_wallet', False]  # networkWallet, isOpen

        assert kwallet_keyring.is_unlocked is False

        mock_get_result.assert_any_call("isOpen", args=['test_wallet'])
        assert all(call.args[0] != 'open' for call in mock_get_result.call_args_list)
    mock_dialog.assert_not_called()
    assert kwallet_keyring.handle == -1


@patch('vorta.keyring.kwallet.QInputDialog.getText', return_value=('', False))
def test_is_unlocked_no_network_wallet(mock_dialog, kwallet_keyring):
    with patch.object(kwallet_keyring, 'get_result', return_value=None):
        assert kwallet_keyring.is_unlocked is False
    mock_dialog.assert_not_called()
    assert kwallet_keyring.handle == -1


def test_is_unlocked_wallet_opened_elsewhere(kwallet_keyring):
    with patch.object(kwallet_keyring, 'get_result') as mock_get_result:
        mock_get_result.side_effect = ['test_wallet', True]
        assert kwallet_keyring.is_unlocked is True
    assert kwallet_keyring.handle == -1


def test_open_handle_needs_no_dbus(kwallet_keyring):
    kwallet_keyring.handle = 42
    with patch.object(kwallet_keyring, 'get_result') as mock_get_result:
        assert kwallet_keyring.is_unlocked is True
        assert kwallet_keyring.try_unlock() is True
        mock_get_result.assert_not_called()


def test_try_unlock_returns_true_on_success(kwallet_keyring):
    with patch.object(kwallet_keyring, 'get_result') as mock_get_result:
        mock_get_result.side_effect = ['test_wallet', 42]
        assert kwallet_keyring.try_unlock() is True
    assert kwallet_keyring.handle == 42


@patch('vorta.keyring.kwallet.QInputDialog.getText', return_value=('', False))
def test_try_unlock_returns_false_when_dialog_cancelled(mock_dialog, kwallet_keyring):
    with patch.object(kwallet_keyring, 'get_result', return_value=None):
        assert kwallet_keyring.try_unlock() is False
    mock_dialog.assert_called_once()
    assert kwallet_keyring.handle == -2


def test_try_unlock_returns_false_when_open_fails(kwallet_keyring):
    with patch.object(kwallet_keyring, 'get_result') as mock_get_result:
        mock_get_result.side_effect = ['test_wallet', None]
        assert kwallet_keyring.try_unlock() is False
    assert kwallet_keyring.handle == -2


def test_try_unlock_returns_false_when_open_denied(kwallet_keyring):
    with patch.object(kwallet_keyring, 'get_result') as mock_get_result:
        mock_get_result.side_effect = ['test_wallet', -1]
        assert kwallet_keyring.try_unlock() is False
