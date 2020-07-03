from PyQt5 import QtDBus
from vorta.keyring.abc import VortaKeyring
import os


class VortaKWallet5Keyring(VortaKeyring):
    """A wrapper for the dbus package to support the custom keyring backend"""

    folderName = 'Vorta'
    serviceName = "org.kde.kwalletd5"
    objectPath = "/modules/kwalletd5"
    interfaceName = 'org.kde.KWallet'

    def __init__(self):
        """
        Test whether DBus and KDEWallet are available.
        """
        self.iface = QtDBus.QDBusInterface(
            self.serviceName,
            self.objectPath,
            self.interfaceName,
            QtDBus.QDBusConnection.sessionBus())

    def set_password(self, service, repo_url, password):
        self.iface.call("writePassword", [self.handle, self.folderName, repo_url, password, service])

    def get_password(self, service, repo_url):
        if not self.open():
            return None
        if not self.get_result("hasEntry", [self.handle, self.folderName, repo_url, service]):
            return None
        return self.get_result("readPassword", [self.handle, self.folderName, repo_url, service])

    def get_result(self, method, args):
        if len(args) > 0:
            result = self.iface.callWithArgumentList(QtDBus.QDBus.AutoDetect, method, args)
        else:
            result = self.iface.call(QtDBus.QDBus.AutoDetect, method)
        return result.arguments()[0]

    def open(self):
        self.get_handle()
        return self.handle > 0

    def get_handle(self):
        walletName = self.get_result("networkWallet", [])
        output = os.popen(f"qdbus {self.serviceName} {self.objectPath} open {walletName} 0 vorta-repo").read()
        try:
            self.handle = int(output)
        except ValueError:
            self.handle = -1  # Same value as not unlocked

    @property
    def valid(self):
        if self.iface.isValid():
            return bool(self.get_result("isEnabled", []))
        else:
            return False


class VortaKWallet4Keyring(VortaKWallet5Keyring):
    serviceName = "org.kde.kwalletd"
    objectPath = "/modules/kwalletd"
