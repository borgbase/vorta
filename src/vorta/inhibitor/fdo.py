import logging
from typing import Optional

from PyQt6 import QtDBus
from PyQt6.QtCore import QMetaType, QObject, QVariant

from vorta.dbus import DBusException, get_result
from vorta.inhibitor.abc import Inhibitor

logger = logging.getLogger(__name__)


_INHIBIT_SUSPEND = 4


class FdoInhibitor(Inhibitor):
    def __init__(self, name: str):
        super().__init__(name)
        self._bus = QtDBus.QDBusConnection.sessionBus()
        if not self._bus.isConnected():
            raise DBusException("cannot connect to session bus")
        self._inhibit_request_handle: Optional[str] = None
        self._inhibit_request: Optional[QtDBus.QDBusInterface] = None

    def inhibit(self):
        try:
            inhibit_iface = QtDBus.QDBusInterface(
                'org.freedesktop.portal.Desktop',
                '/org/freedesktop/portal/desktop',
                'org.freedesktop.portal.Inhibit',
                self._bus,
            )
            if not inhibit_iface.isValid():
                raise DBusException("invalid desktop dbus interface")

            # enforce uint through the call
            flags = QVariant(_INHIBIT_SUSPEND)
            flags.convert(QMetaType(QMetaType.Type.UInt.value))

            result = inhibit_iface.call('Inhibit', '', flags, {"reason": self._name})
            self._inhibit_request_handle = get_result(result)

            self._inhibit_request = QtDBus.QDBusInterface(
                "org.freedesktop.portal.Desktop",
                self._inhibit_request_handle,
                "org.freedesktop.portal.Request",
                QtDBus.QDBusConnection.sessionBus(),
            )

            logger.debug("inhibit acquired: %s", self._inhibit_request_handle)
        except Exception:
            logger.warning("failed to inhibit", exc_info=True)
            self._inhibit_request = None

    def uninhibit(self):
        if self._inhibit_request is not None:
            try:
                logger.debug("released inhibit: %s", self._inhibit_request_handle)
                self._inhibit_request.call("Close")
            except Exception:
                logger.warning("failed to release inhibit: %s", self._inhibit_request_handle)
        else:
            logger.warning("no active inhibit")


class FdoDesktopDBusAdaptor(QObject):
    """
    Adapter to the org.freedesktop.login1 DBus interface.
    """

    @classmethod
    def get_desktop_adaptor(cls) -> 'FdoDesktopDBusAdaptor':
        bus = QtDBus.QDBusConnection.systemBus()
        if not bus.isConnected():
            raise DBusException("Can't connect to system bus")
        return cls(parent=None, bus=bus)

    def __init__(self, parent, bus):
        super().__init__(parent)
        self._pm = QtDBus.QDBusInterface(
            'org.freedesktop.portal.Desktop', '/org/freedesktop/portal/desktop', 'org.freedesktop.portal.Inhibit', bus
        )

    def inhibit(self, name: str) -> QtDBus.QDBusInterface:
        return self._pm.call('Inhibit', 'sleep', 'Vorta', name, 'block')
