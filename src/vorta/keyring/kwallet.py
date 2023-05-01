import logging
import os

from PyQt6 import QtDBus
from PyQt6.QtCore import QMetaType, QVariant

from vorta.keyring.abc import VortaKeyring

logger = logging.getLogger(__name__)


class VortaKWallet5Keyring(VortaKeyring):
    """A wrapper for the qtdbus package to support the custom keyring backend"""

    folder_name = 'Vorta'
    service_name = "org.kde.kwalletd5"
    object_path = "/modules/kwalletd5"
    interface_name = 'org.kde.KWallet'

    def __init__(self):
        """
        Test whether DBus and KDEWallet are available.
        """
        self.iface = QtDBus.QDBusInterface(
            self.service_name,
            self.object_path,
            self.interface_name,
            QtDBus.QDBusConnection.sessionBus(),
        )
        self.handle = -1
        if not (self.iface.isValid() and self.get_result("isEnabled") is True):
            raise KWalletNotAvailableException

    def set_password(self, service, repo_url, password):
        self.get_result(
            "writePassword",
            args=[self.handle, self.folder_name, repo_url, password, service],
        )
        logger.debug(f"Saved password for repo {repo_url}")

    def get_password(self, service, repo_url):
        if not (
            self.is_unlocked and self.get_result("hasEntry", args=[self.handle, self.folder_name, repo_url, service])
        ):
            return None
        password = self.get_result("readPassword", args=[self.handle, self.folder_name, repo_url, service])
        logger.debug(f"Retrieved password for repo {repo_url}")
        return password

    def get_result(self, method, args=[]):
        if args:
            result = self.iface.callWithArgumentList(QtDBus.QDBus.CallMode.AutoDetect, method, args)
        else:
            result = self.iface.call(QtDBus.QDBus.CallMode.AutoDetect, method)
        return result.arguments()[0]

    @property
    def is_unlocked(self):
        self.try_unlock()
        return self.handle > 0

    def try_unlock(self):
        wallet_name = self.get_result("networkWallet")
        wId = QVariant(0)
        wId.convert(QMetaType(QMetaType.Type.LongLong.value))
        output = self.get_result("open", args=[wallet_name, wId, 'vorta-repo'])
        try:
            self.handle = int(output)
        except ValueError:  # For when kwallet is disabled or dbus otherwise broken
            self.handle = -2

    @classmethod
    def get_priority(cls):
        return 6 if "KDE" in os.getenv("XDG_CURRENT_DESKTOP", "") else 4

    @property
    def is_system(self):
        return True


class KWalletNotAvailableException(Exception):
    pass
