# ruff: noqa

"""
A dirty objc implementation to access the macOS Keychain. Because the
keyring implementation was causing trouble when used together with other
objc modules.

Adapted from https://gist.github.com/apettinen/5dc7bf1f6a07d148b2075725db6b1950
"""

import logging
import sys
from ctypes import c_char

import objc
from Foundation import NSBundle

from .abc import VortaKeyring

logger = logging.getLogger(__name__)


class VortaDarwinKeyring(VortaKeyring):
    """Homemade macOS Keychain Service"""

    login_keychain = None

    def _set_keychain(self):
        """
        Lazy import to avoid conflict with pytest-xdist.
        """

        Security = NSBundle.bundleWithIdentifier_('com.apple.security')

        # https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/ObjCRuntimeGuide/Articles/ocrtTypeEncodings.html
        S_functions = [
            ('SecKeychainGetTypeID', b'I'),
            ('SecKeychainItemGetTypeID', b'I'),
            (
                'SecKeychainAddGenericPassword',
                b'i^{OpaqueSecKeychainRef=}I*I*I*o^^{OpaqueSecKeychainItemRef}',
            ),
            ('SecKeychainOpen', b'i*o^^{OpaqueSecKeychainRef}'),
            (
                'SecKeychainFindGenericPassword',
                b'i@I*I*o^Io^^{OpaquePassBuff}o^^{OpaqueSecKeychainItemRef}',
            ),
            ('SecKeychainGetStatus', b'i^{OpaqueSecKeychainRef=}o^I'),
            ('SecKeychainItemDelete', b'i^{OpaqueSecKeychainItemRef=}'),
        ]

        objc.loadBundleFunctions(Security, globals(), S_functions)

        objc.registerCFSignature('SecKeychainRef', b'^{OpaqueSecKeychainRef=}', SecKeychainGetTypeID())
        objc.registerCFSignature(
            'SecKeychainItemRef',
            b'^{OpaqueSecKeychainItemRef=}',
            SecKeychainItemGetTypeID(),
        )

        try:
            objc.createOpaquePointerType('PassBuffRef', b'^{OpaquePassBuff=}', None)
        except objc.error:
            # Type already registered (can happen in tests or when module is reloaded)
            pass

        # Get the login keychain
        result, login_keychain = SecKeychainOpen(b'login.keychain', None)
        self.login_keychain = login_keychain

    def set_password(self, service, repo_url, password):
        if not self.login_keychain:
            self._set_keychain()

        # Delete existing password (required for macOS)
        self.delete_password(service, repo_url)

        SecKeychainAddGenericPassword(
            self.login_keychain,
            len(service.encode()),
            service.encode(),
            len(repo_url.encode()),
            repo_url.encode(),
            len(password.encode()),
            password.encode(),
            None,
        )

        logger.debug(f"Saved password for repo {repo_url}")

    def delete_password(self, service, repo_url):
        if not self.login_keychain:
            self._set_keychain()
        try:
            result, password_length, password_buffer, keychain_item = SecKeychainFindGenericPassword(
                self.login_keychain,
                len(service),
                service.encode(),
                len(repo_url),
                repo_url.encode(),
                None,
                None,
                None,
            )
            if result == 0 and keychain_item:
                del_result = SecKeychainItemDelete(keychain_item)
                if del_result == 0:
                    logger.debug(f"Deleted password for repo {repo_url}")
                else:
                    logger.debug(
                        f"Failed to delete password for repo {repo_url}, SecKeychainItemDelete returned {del_result}"
                    )
        except Exception as e:
            logger.debug(f"No password to delete for repo {repo_url}: {e}")

    def get_password(self, service, repo_url):
        if not self.login_keychain:
            self._set_keychain()

        (
            result,
            password_length,
            password_buffer,
            keychain_item,
        ) = SecKeychainFindGenericPassword(
            self.login_keychain,
            len(service),
            service.encode(),
            len(repo_url),
            repo_url.encode(),
            None,
            None,
            None,
        )
        password = None
        if (result == 0) and (password_length != 0):
            # We apparently were able to find a password
            password = _resolve_password(password_length, password_buffer)
        logger.debug(f"Retrieved password for repo {repo_url}")
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
    s = (c_char * password_length).from_address(password_buffer.__pointer__)[:]
    return s.decode()
