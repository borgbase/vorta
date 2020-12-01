"""
Set the most appropriate Keyring backend for the current system.
For Linux not every system has SecretService available, so it will
fall back to a simple database keystore if needed.
"""
import sys


class VortaKeyring:
    _keyring = None

    @classmethod
    def get_keyring(cls):
        """
        Attempts to get secure keyring at runtime if current keyring is insecure.
        Once it finds a secure keyring, it wil always use that keyring
        """
        if cls._keyring is None or not cls._keyring.is_primary:
            if sys.platform == 'darwin':  # Use Keychain on macOS
                from .darwin import VortaDarwinKeyring
                cls._keyring = VortaDarwinKeyring()
            else:  # Try to use DBus and Gnome-Keyring (available on Linux and *BSD)
                import secretstorage
                from .secretstorage import VortaSecretStorageKeyring
                try:
                    cls._keyring = VortaSecretStorageKeyring()
                # Save passwords in DB, if all else fails.
                except secretstorage.SecretServiceNotAvailableException:
                    from .db import VortaDBKeyring
                    cls._keyring = VortaDBKeyring()
        return cls._keyring

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
