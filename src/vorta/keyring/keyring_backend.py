"""
Keyring backend implementation
Based on the keyring package
https://github.com/jaraco/keyring/blob/master/keyring/backend.py
"""

import abc

from . import keyring_errors


class KeyringBackend:
    """The abstract base class of the keyring, every backend must implement
    this interface.
    """

    @abc.abstractmethod
    def get_password(self, service, username):
        """Get password of the username for the service
        """
        return None

    @abc.abstractmethod
    def set_password(self, service, username, password):
        """Set password for the username of the service.
        If the backend cannot store passwords, raise
        NotImplementedError.
        """
        raise keyring_errors.PasswordSetError("reason")
