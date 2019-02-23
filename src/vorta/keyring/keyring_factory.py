"""
Set the most appropriate Keyring backend for the current system.
For Linux not every system has SecretService available, so it will
fall back to a simple database keystore if needed.
"""
import sys


class VortaKeyring:
    @classmethod
    def get_keyring(cls):
        if sys.platform == 'darwin':
            from .keyring_darwin import DarwinKeyring
            return DarwinKeyring()
        elif sys.platform.startswith('linux'):
            from .keyring_secretstorage import VortaSecretStorageKeyring, secretstorage
            try:
                return VortaSecretStorageKeyring()
            except secretstorage.SecretServiceNotAvailableException:
                from .keyring_db import VortaDBKeyring
                return VortaDBKeyring()
        else:
            from .keyring_db import VortaDBKeyring
            return VortaDBKeyring()

    def set_password(self):
        raise NotImplementedError

    def get_password(self):
        raise NotImplementedError
