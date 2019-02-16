class KeyringError(Exception):
    """Base class for exceptions in keyring
    """


class PasswordSetError(KeyringError):
    """Raised when the password can't be set.
    """


class PasswordDeleteError(KeyringError):
    """Raised when the password can't be deleted.
    """


class InitError(KeyringError):
    """Raised when the keyring could not be initialised
    """


class KeyringLocked(KeyringError):
    """Raised when the keyring could not be initialised
    """
