"""
Common utilities for dbus services like network manager and inhibitor.

This should not be imported unless the platform is known to support dbus.
"""

from typing import Any

from PyQt6 import QtDBus


def read_dbus_property(obj, property):
    # QDBusInterface.property() didn't work for some reason
    props = QtDBus.QDBusInterface(obj.service(), obj.path(), 'org.freedesktop.DBus.Properties', obj.connection())
    msg = props.call('Get', obj.interface(), property)
    return get_result(msg)


def get_result(msg: QtDBus.QDBusMessage) -> Any:
    if msg.type() == msg.MessageType.ReplyMessage:
        return msg.arguments()[0]
    else:
        raise DBusException("DBus call failed: {}".format(msg.arguments()))


class DBusException(Exception):
    """Failed to call a DBus method"""
