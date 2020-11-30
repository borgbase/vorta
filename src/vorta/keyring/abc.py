"""
Set the most appropriate Keyring backend for the current system.
For Linux not every system has SecretService available, so it will
fall back to a simple database keystore if needed.
"""
import sys

_keyring = None


class VortaKeyring:
    def set_password(self, service, repo_url, password):
        raise NotImplementedError

    def get_password(self, service, repo_url):
        """
        Retrieve a password from the underlying store. Return None if not found.
        """
        raise NotImplementedError

    @property
    def is_primary(self):
        """
        Return True if the current subclass is the system's primary keychain mechanism,
        rather than a fallback (like our own VortaDBKeyring).
        """
        return True


def get_keyring():
    """
    Attempts to get secure keyring at runtime if current keyring is insecure.
    Once it finds a secure keyring, it wil always use that keyring
    """
    global _keyring
    if _keyring is None or not _keyring.is_primary:
        if sys.platform == 'darwin':  # Use Keychain on macOS
            from .darwin import VortaDarwinKeyring
            _keyring = VortaDarwinKeyring()
        else:  # Try to use DBus and Gnome-Keyring (available on Linux and *BSD)
            import secretstorage
            from .secretstorage import VortaSecretStorageKeyring
            try:
                _keyring = VortaSecretStorageKeyring()
            except secretstorage.SecretServiceNotAvailableException:  # Try to use KWallet
                from .kwallet import VortaKWallet5Keyring, KWalletNotAvailableException
                try:
                    _keyring = VortaKWallet5Keyring()
                except KWalletNotAvailableException:  # Save passwords in DB, if all else fails.
                    from .db import VortaDBKeyring
                    _keyring = VortaDBKeyring()
    return _keyring
