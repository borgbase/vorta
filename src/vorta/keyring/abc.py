"""
Set the most appropriate Keyring backend for the current system.
For Linux not every system has SecretService available, so it will
fall back to a simple database keystore if needed.
"""
import sys


class VortaKeyring:
    @classmethod
    def get_keyring(cls):
        if sys.platform == 'darwin':  # Use Keychain on macOS
            from .darwin import VortaDarwinKeyring
            return VortaDarwinKeyring()
        else:
            from .kwallet import VortaKWallet5Keyring
            if VortaKWallet5Keyring().is_valid:
                return VortaKWallet5Keyring()
            else:
                from .kwallet import VortaKWallet4Keyring
                if VortaKWallet4Keyring().is_valid:
                    return VortaKWallet4Keyring()
                else:
                    import secretstorage
                    from .secretstorage import VortaSecretStorageKeyring
                    try:
                        return VortaSecretStorageKeyring()
                    # Save passwords in DB, if all else fails.
                    except secretstorage.SecretServiceNotAvailableException:
                        from .db import VortaDBKeyring
                        return VortaDBKeyring()

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
