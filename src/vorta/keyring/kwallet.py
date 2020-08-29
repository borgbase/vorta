from PyQt5 import QtDBus
from PyQt5.QtCore import QVariant
from vorta.keyring.abc import VortaKeyring


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
        self.iface.call("writePassword", args=[self.handle, self.folderName, repo_url, password, service])

    def get_password(self, service, repo_url):
        if not (self.open() and self.get_result("hasEntry", args=[self.handle, self.folderName, repo_url, service])):
            return None
        return self.get_result("readPassword", args=[self.handle, self.folderName, repo_url, service])

    def get_result(self, method, args=[]):
        if args:
            result = self.iface.callWithArgumentList(QtDBus.QDBus.AutoDetect, method, args)
        else:
            result = self.iface.call(QtDBus.QDBus.AutoDetect, method)
        return result.arguments()[0]

    def open(self):
        self.get_handle()
        return self.handle > 0

    def get_handle(self):
        walletName = self.get_result("networkWallet")
        wId = QVariant(0)
        wId.convert(4)
        output = self.get_result("open", args=[walletName, wId, 'vorta-repo'])
        self.handle = int(output)

    @property
    def valid(self):
        return self.iface.isValid() and bool(self.get_result("isEnabled"))


class VortaKWallet4Keyring(VortaKWallet5Keyring):
    serviceName = "org.kde.kwalletd"
    objectPath = "/modules/kwalletd"
