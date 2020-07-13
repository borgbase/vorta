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
        self.iface.call("writePassword", [self.handle, self.folderName, repo_url, password, service]).arguments()[0]

    def get_password(self, service, repo_url):
        if not self.open():
            return None
        if not self.iface.callWithArgumentList(
            QtDBus.QDBus.AutoDetect, "hasEntry", [
                self.handle, self.folderName, repo_url, service]).arguments()[0]:
            return None
        return self.iface.callWithArgumentList(
            QtDBus.QDBus.AutoDetect, "readPassword", [
                self.handle, self.folderName, repo_url, service]).arguments()[0]

    def open(self):
        self.get_handle()
        return self.handle > 0

    def get_handle(self):
        walletName = self.iface.call(QtDBus.QDBus.AutoDetect, "networkWallet").arguments()[0]
        wId = QVariant(0)
        wId.convert(4)
        output = self.iface.callWithArgumentList(
            QtDBus.QDBus.AutoDetect, "open", [
                walletName, wId, 'vorta-repo']).arguments()[0]
        self.handle = int(output)

    @property
    def valid(self):
        if self.iface.isValid():
            return bool(self.iface.call(QtDBus.QDBus.AutoDetect, "isEnabled").arguments()[0])
        else:
            return False


class VortaKWallet4Keyring(VortaKWallet5Keyring):
    serviceName = "org.kde.kwalletd"
    objectPath = "/modules/kwalletd"
