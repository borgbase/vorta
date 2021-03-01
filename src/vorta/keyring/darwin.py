# flake8: noqa

"""
A dirty objc implementation to access the macOS Keychain. Because the
keyring implementation was causing trouble when used together with other
objc modules.

Adapted from https://gist.github.com/apettinen/5dc7bf1f6a07d148b2075725db6b1950
"""
import sys
from .abc import VortaKeyring


class VortaDarwinKeyring(VortaKeyring):
    """Homemade macOS Keychain Service"""

    login_keychain = None

    def _set_keychain(self):
        """
        Lazy import to avoid conflict with pytest-xdist.
        """
        import objc
        from Foundation import NSBundle
        Security = NSBundle.bundleWithIdentifier_('com.apple.security')

        # https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/ObjCRuntimeGuide/Articles/ocrtTypeEncodings.html
        S_functions = [
            ('SecKeychainGetTypeID', b'I'),
            ('SecKeychainItemGetTypeID', b'I'),
            ('SecKeychainAddGenericPassword', b'i^{OpaqueSecKeychainRef=}I*I*I*o^^{OpaqueSecKeychainItemRef}'),
            ('SecKeychainOpen', b'i*o^^{OpaqueSecKeychainRef}'),
            ('SecKeychainFindGenericPassword', b'i@I*I*o^Io^^{OpaquePassBuff}o^^{OpaqueSecKeychainItemRef}'),
            ('SecKeychainGetStatus', b'i^{OpaqueSecKeychainRef=}o^I'),
        ]

        objc.loadBundleFunctions(Security, globals(), S_functions)

        SecKeychainRef = objc.registerCFSignature('SecKeychainRef', b'^{OpaqueSecKeychainRef=}', SecKeychainGetTypeID())
        SecKeychainItemRef = objc.registerCFSignature(
            'SecKeychainItemRef', b'^{OpaqueSecKeychainItemRef=}', SecKeychainItemGetTypeID())

        PassBuffRef = objc.createOpaquePointerType('PassBuffRef', b'^{OpaquePassBuff=}', None)

        # Get the login keychain
        result, login_keychain = SecKeychainOpen(b'login.keychain', None)
        self.login_keychain = login_keychain

    def set_password(self, service, repo_url, password):
        if not self.login_keychain:
            self._set_keychain()

        SecKeychainAddGenericPassword(
            self.login_keychain,
            len(service.encode()), service.encode(),
            len(repo_url.encode()), repo_url.encode(),
            len(password.encode()), password.encode(),
            None)

    def get_password(self, service, repo_url):
        if not self.login_keychain:
            self._set_keychain()

        result, password_length, password_buffer, keychain_item = SecKeychainFindGenericPassword(
            self.login_keychain, len(service), service.encode(), len(repo_url), repo_url.encode(), None, None, None)
        password = None
        if (result == 0) and (password_length != 0):
            # We apparently were able to find a password
            password = _resolve_password(password_length, password_buffer)
        return password

    @property
    def is_unlocked(self):
        kSecUnlockStateStatus = 1

        if not self.login_keychain:
            self._set_keychain()

        result, keychain_status = SecKeychainGetStatus(self.login_keychain, None)

        return keychain_status & kSecUnlockStateStatus

    @classmethod
    def get_priority(cls):
        if sys.platform == 'darwin':
            return 8
        else:
            raise RuntimeError('Only available on macOS')

    @property
    def is_system(self):
        return True


def _resolve_password(password_length, password_buffer):
    from ctypes import c_char
    s = (c_char*password_length).from_address(password_buffer.__pointer__)[:]
    return s.decode()

