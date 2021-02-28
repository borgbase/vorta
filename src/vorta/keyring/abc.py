"""
Set the most appropriate Keyring backend for the current system.
For Linux not every system has SecretService available, so it will
fall back to a simple database keystore if needed.
"""
import sys
from pkg_resources import parse_version
from vorta.i18n import trans_late


class VortaKeyring:
    _keyring = None

    @classmethod
    def get_keyring(cls):
        """
        Choose available Keyring or save passwords to settings database.

        Will always use Keychain on macOS. Will try KWallet and then Secret
        Storage on Linux and *BSD. If none are available or usage of system
        keychain is disabled, fall back to saving passwords to DB.
        """

        from vorta.models import SettingsModel
        from .db import VortaDBKeyring

        if SettingsModel.get(key='use_system_keyring').value:
            if cls._keyring is None or not cls._keyring.is_system:
                # macOS: Only Keychain available
                if sys.platform == 'darwin':
                    from .darwin import VortaDarwinKeyring
                    cls._keyring = VortaDarwinKeyring()
                else:
                    # Others: Try KWallet first
                    from .kwallet import VortaKWallet5Keyring, KWalletNotAvailableException
                    try:
                        cls._keyring = VortaKWallet5Keyring()
                    except KWalletNotAvailableException:
                        # Try to use DBus and Gnome Keyring (available on Linux and *BSD)
                        # Put this last as Gnome Keyring is included by default on many distros
                        import secretstorage
                        from .secretstorage import VortaSecretStorageKeyring

                        # Secret Storage has two different libraries based on version
                        if parse_version(secretstorage.__version__) >= parse_version("3.0.0"):
                            from jeepney.wrappers import DBusErrorResponse as DBusException
                        else:
                            from dbus.exceptions import DBusException
                        try:
                            cls._keyring = VortaSecretStorageKeyring()
                        except (secretstorage.exceptions.SecretStorageException, DBusException):
                            # Fall back to using DB, if all else fails.
                            cls._keyring = VortaDBKeyring()
        else:
            cls._keyring = VortaDBKeyring()

        return cls._keyring

    def get_backend_warning(self):
        if self.is_system:
            return trans_late('utils', 'Storing password in your password manager.')
        else:
            return trans_late('utils', 'Saving password with Vorta settings.')

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
    def is_system(self):
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
