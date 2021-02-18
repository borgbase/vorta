"""
Set the most appropriate Keyring backend for the current system.
For Linux not every system has SecretService available, so it will
fall back to a simple database keystore if needed.
"""
import sys
from pkg_resources import parse_version


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
            else:
                # Try to use KWallet (KDE)
                from .kwallet import VortaKWallet5Keyring, KWalletNotAvailableException
                try:
                    cls._keyring = VortaKWallet5Keyring()
                except KWalletNotAvailableException:
                    # Try to use DBus and Gnome-Keyring (available on Linux and *BSD)
                    # Put this last as gnome keyring is included by default on many distros
                    import secretstorage
                    from .secretstorage import VortaSecretStorageKeyring

                    # secretstorage has two different libraries based on version
                    if parse_version(secretstorage.__version__) >= parse_version("3.0.0"):
                        from jeepney.wrappers import DBusErrorResponse as DBusException
                    else:
                        from dbus.exceptions import DBusException

                    try:
                        cls._keyring = VortaSecretStorageKeyring()
                    except (secretstorage.exceptions.SecretStorageException, DBusException):
                        # Save passwords in DB, if all else fails.
                        from .db import VortaDBKeyring
                        cls._keyring = VortaDBKeyring()
        return cls._keyring

    def set_password(self, service, repo_url, password):
        """
        Writes a password to the underlying store.
        """
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

    @property
    def is_unlocked(self):
        """
        Try to unlock the keyring.
        Returns True if the keyring is open. Return False if it is closed or locked
        """
        raise NotImplementedError
