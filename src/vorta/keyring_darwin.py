"""
A dirty objc implementation to access the macOS Keychain. Because the
keyring implementation was causing trouble when used together with other
objc modules.

From https://gist.github.com/apettinen/5dc7bf1f6a07d148b2075725db6b1950
"""

import keyring
import objc
from ctypes import c_char
from Foundation import NSBundle
Security = NSBundle.bundleWithIdentifier_('com.apple.security')

S_functions = [
    ('SecKeychainGetTypeID', b'I'),
    ('SecKeychainItemGetTypeID', b'I'),
    ('SecKeychainAddGenericPassword', b'i^{OpaqueSecKeychainRef=}I*I*I*o^^{OpaqueSecKeychainItemRef}'),
    ('SecKeychainOpen', b'i*o^^{OpaqueSecKeychainRef}'),
    ('SecKeychainFindGenericPassword', b'i@I*I*o^Io^^{OpaquePassBuff}o^^{OpaqueSecKeychainItemRef}'),
]

objc.loadBundleFunctions(Security, globals(), S_functions)

SecKeychainRef = objc.registerCFSignature(
    'SecKeychainRef', b'^{OpaqueSecKeychainRef=}', SecKeychainGetTypeID())  # noqa: F821
SecKeychainItemRef = objc.registerCFSignature(
    'SecKeychainItemRef', b'^{OpaqueSecKeychainItemRef=}', SecKeychainItemGetTypeID())  # noqa: F821
PassBuffRef = objc.createOpaquePointerType(
    "PassBuffRef", b"^{OpaquePassBuff=}", None)


def resolve_password(password_length, password_buffer):
    return (c_char * password_length).from_address(password_buffer.__pointer__)[:].decode('utf-8')


# Get the login keychain
result, login_keychain = SecKeychainOpen(b'login.keychain', None)  # noqa: F821


class VortaDarwinKeyring(keyring.backend.KeyringBackend):
    """Homemade macOS Keychain Service"""
    @classmethod
    def priority(cls):
        return 5

    def set_password(self, service, repo_url, password):
        result, keychain_item = SecKeychainAddGenericPassword(  # noqa: F821
            login_keychain, len(service), service, len(repo_url), repo_url, len(password), password, None)

    def get_password(self, service, repo_url):
        result, password_length, password_buffer, keychain_item = SecKeychainFindGenericPassword(  # noqa: F821
            login_keychain, len(service), service.encode(), len(repo_url), repo_url.encode(), None, None, None)
        password = None
        if (result == 0) and (password_length != 0):
            # We apparently were able to find a password
            password = resolve_password(password_length, password_buffer)
        return password

    def delete_password(self, service, repo_url):
        pass
