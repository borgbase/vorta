"""
Core API functions and initialization routines.
Based on the keyring package
https://github.com/jaraco/keyring/blob/master/keyring/core.py
"""

from . import keyring_backend

_keyring_backend = None


def set_keyring(keyring):
    """Set current keyring backend.
    """
    global _keyring_backend
    if not isinstance(keyring, keyring_backend.KeyringBackend):
        raise TypeError("The keyring must be a subclass of KeyringBackend")
    _keyring_backend = keyring


def get_keyring():
    """Get current keyring backend.
    """
    return _keyring_backend


def get_password(service_name, username):
    """Get password from the specified service.
    """
    return _keyring_backend.get_password(service_name, username)


def set_password(service_name, username, password):
    """Set password for the user in the specified service.
    """
    _keyring_backend.set_password(service_name, username, password)
