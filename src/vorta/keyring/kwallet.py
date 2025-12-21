import logging
import os

from PyQt6 import QtDBus
from PyQt6.QtCore import QMetaType, QVariant
from PyQt6.QtDBus import QDBusMessage
from PyQt6.QtWidgets import QInputDialog

from vorta.i18n import translate
from vorta.keyring.abc import VortaKeyring

logger = logging.getLogger(__name__)


class VortaKWallet5Keyring(VortaKeyring):
    """A wrapper for the qtdbus package to support the custom keyring backend."""

    folder_name = "Vorta"
    service_name = "org.kde.kwalletd5"
    object_path = "/modules/kwalletd5"
    interface_name = "org.kde.KWallet"

    def __init__(self):
        """Initialize the KWallet keyring and test DBus and KDEWallet availability.

        Raises:
            KWalletNotAvailableException: If KWallet is not available or enabled.
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
        """Set a password in the KWallet.

        Args:
            service: The service name.
            repo_url: The repository URL.
            password: The password to store.
        """
        self.get_result(
            "writePassword",
            args=[self.handle, self.folder_name, repo_url, password, service],
        )
        logger.debug(f"Saved password for repo {repo_url}")

    def delete_password(self, service, repo_url):
        try:
            self.get_result(
                "removeEntry",
                args=[self.handle, self.folder_name, repo_url, service],
            )
            logger.debug(f"Deleted password for repo {repo_url}")
        except Exception as e:
            logger.debug(f"No password to delete for repo {repo_url}: {e}")

    def get_password(self, service, repo_url):
        """Retrieve a password from the KWallet.

        Args:
            service: The service name.
            repo_url: The repository URL.

        Returns:
            str or None: The retrieved password, or None if not found.
        """
        if not (
            self.is_unlocked and self.get_result("hasEntry", args=[self.handle, self.folder_name, repo_url, service])
        ):
            return None
        password = self.get_result("readPassword", args=[self.handle, self.folder_name, repo_url, service])
        logger.debug(translate("KWallet", f"Retrieved password for repo {repo_url}"))
        return password

    def get_result(self, method, args=[]):
        """Call a DBus method and return the raw result.

        Args:
            method: The DBus method to call.
            args: The arguments to pass to the method.

        Returns:
            The raw result from the DBus call, or None on error.
        """
        if args:
            result = self.iface.callWithArgumentList(QtDBus.QDBus.CallMode.AutoDetect, method, args)
        else:
            result = self.iface.call(QtDBus.QDBus.CallMode.AutoDetect, method)

        if result.type() == QDBusMessage.MessageType.ErrorMessage:
            logger.error(translate("KWallet", f"Method '{method}' returned an error message."))
            return None

        arguments = result.arguments()
        return arguments[0] if arguments else None

    @property
    def is_unlocked(self):
        """Check if the wallet is unlocked.

        Returns:
            bool: True if the wallet is unlocked, False otherwise.
        """
        self.try_unlock()
        return self.handle > 0

    def try_unlock(self):
        """Attempt to unlock the wallet.

        Raises:
            ValueError: If the wallet name is invalid or unlocking fails.
        """
        wallet_name = self.get_result("networkWallet")
        if wallet_name is None:
            wallet_name, ok = QInputDialog.getText(
                None,
                translate("KWallet", "Create Wallet"),
                translate("KWallet", "Enter a name for the new wallet:"),
            )
            if not ok or not wallet_name.strip():
                logger.error(
                    translate(
                        "KWallet",
                        "Could not determine a valid wallet name. Aborting unlock attempt.",
                    )
                )
                self.handle = -2
                return

        wId = QVariant(0)
        wId.convert(QMetaType(QMetaType.Type.LongLong.value))
        output = self.get_result("open", args=[wallet_name, wId, "vorta-repo"])
        if output is None:
            logger.error(translate("KWallet", "Failed to open wallet. Aborting unlock attempt."))
            self.handle = -2
            return

        try:
            self.handle = int(output)
        except (ValueError, TypeError):  # For when kwallet is disabled or dbus otherwise broken
            self.handle = -2

    @classmethod
    def get_priority(cls):
        """Get the priority of the keyring.

        Returns:
            int: The priority value.
        """
        return 6 if "KDE" in os.getenv("XDG_CURRENT_DESKTOP", "") else 4

    @property
    def is_system(self):
        """Check if the keyring is a system keyring.

        Returns:
            bool: True if it is a system keyring, False otherwise.
        """
        return True


class KWalletNotAvailableException(Exception):
    """Exception raised when KWallet is not available."""

    pass
