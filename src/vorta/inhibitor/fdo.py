import logging
import os

from PyQt6 import QtDBus
from PyQt6.QtCore import QObject

from vorta.dbus import DBusException, get_result
from vorta.inhibitor.abc import Inhibitor

logger = logging.getLogger(__name__)


class FdoInhibitor(Inhibitor):
    def __init__(self, name: str):
        super().__init__(name)
        self._pm = FdoLogin1DBusAdaptor.get_login1_adaptor()

    def inhibit(self):
        try:
            self._fd = get_result(self._pm.inhibit(self._name))
            logger.debug("acquired power management inhibitor: %s", self._name)
        except DBusException:
            logger.exception("Failed to activate power management inhibitor")

    def uninhibit(self):
        if self._fd is not None:
            os.close(self._fd.fileDescriptor())
            logger.debug("released power management inhibitor: %s", self._name)
        else:
            logger.warning("power management inhibitor was not active")
        self._fd = None


class FdoLogin1DBusAdaptor(QObject):
    """
    Adapter to the org.freedesktop.login1 DBus interface.
    """

    @classmethod
    def get_login1_adaptor(cls) -> 'FdoLogin1DBusAdaptor':
        bus = QtDBus.QDBusConnection.systemBus()
        if not bus.isConnected():
            raise UnsupportedException("Can't connect to system bus")
        return cls(parent=None, bus=bus)

    def __init__(self, parent, bus):
        super().__init__(parent)
        self._pm = QtDBus.QDBusInterface(
            'org.freedesktop.login1', '/org/freedesktop/login1', 'org.freedesktop.login1.Manager', bus
        )

    def inhibit(self, name: str) -> QtDBus.QDBusUnixFileDescriptor:
        return self._pm.call('Inhibit', 'shutdown:sleep', 'Vorta', name, 'block')


class UnsupportedException(Exception):
    """PowerManagement is not available"""
