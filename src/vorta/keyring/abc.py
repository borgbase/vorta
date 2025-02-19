import importlib
import logging

from vorta.i18n import trans_late

logger = logging.getLogger(__name__)


class VortaKeyring:
    all_keyrings = [
        ('.db', 'VortaDBKeyring'),
        ('.darwin', 'VortaDarwinKeyring'),
        ('.kwallet', 'VortaKWallet5Keyring'),
        ('.secretstorage', 'VortaSecretStorageKeyring'),
    ]

    @classmethod
    def get_keyring(cls):
        """
        Choose available Keyring. First assign a score and then try to initialize it.
        """
        available_keyrings = []
        for _module, _class in cls.all_keyrings:
            try:
                keyring = getattr(importlib.import_module(_module, package='vorta.keyring'), _class)
                available_keyrings.append((keyring, keyring.get_priority()))
            except Exception as e:
                logger.debug(e)
                continue

        for keyring, _ in sorted(available_keyrings, key=lambda k: k[1], reverse=True):
            try:
                instance = keyring()
                logger.debug(f"Using {keyring.__name__}")
                return instance
            except Exception as e:
                logger.debug(e)
                continue

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
        raise NotImplementedError

    @classmethod
    def get_priority(cls):
        """
        Return priority of this keyring on current system. Higher is more important.

        Shout-out to https://github.com/jaraco/keyring for this idea.
        """
        raise NotImplementedError

    @property
    def is_unlocked(self):
        """
        Try to unlock the keyring.
        Returns True if the keyring is open. Return False if it is closed or locked
        """
        raise NotImplementedError
