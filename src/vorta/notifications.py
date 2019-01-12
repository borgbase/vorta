import sys
import logging
from PyQt5 import QtCore, QtDBus
from vorta.models import SettingsModel

logger = logging.getLogger(__name__)


class VortaNotifications:
    """
    Usage:

    notifier = Notifications.pick()()
    notifier.deliver('blah', 'blah blah')
    """
    @classmethod
    def pick(cls):
        if sys.platform == 'darwin':
            return DarwinNotifications()
        elif QtDBus.QDBusConnection.sessionBus().isConnected():
            return DBusNotifications()
        else:
            logger.warning('could not pick valid notification class')
            return cls()

    def deliver(self, title, text, level='info'):
        """Dummy notifier if we're not on macOS or Linux notifier isn't available."""
        pass

    def notifications_suppressed(self, level):
        """Decide if notification is sent or not based on settings and level."""
        if not SettingsModel.get(key='enable_notifications').value:
            logger.debug('notifications suppressed')
            return True
        if level == 'info' and not SettingsModel.get(key='enable_notifications_success').value:
            logger.debug('success notifications suppressed')
            return True

        logger.debug('notification not suppressed')
        return False


class DarwinNotifications(VortaNotifications):
    """
    Notify via notification center and pyobjc bridge.
    """

    def deliver(self, title, text, level='info'):
        if self.notifications_suppressed(level):
            return

        from Foundation import NSUserNotification, NSUserNotificationCenter
        notification = NSUserNotification.alloc().init()
        notification.setTitle_(title)
        notification.setInformativeText_(text)
        center = NSUserNotificationCenter.defaultUserNotificationCenter()
        if center is not None:  # Only works when run from app bundle.
            return center.deliverNotification_(notification)


class DBusNotifications(VortaNotifications):
    """
    Use qt-dbus to send notifications.

    Adapted from http://codito.in/notifications-in-qt-over-dbus/
    """

    URGENCY = {'info': 1, 'error': 2}

    def __init__(self):
        pass

    def _dbus_notify(self, header, msg, level='info'):
        item = "org.freedesktop.Notifications"
        path = "/org/freedesktop/Notifications"
        interface = "org.freedesktop.Notifications"
        app_name = "vorta"
        v = QtCore.QVariant(12321)  # random int to identify all notifications
        if v.convert(QtCore.QVariant.UInt):
            id_replace = v
        icon = ""
        title = header
        text = msg
        actions_list = QtDBus.QDBusArgument([], QtCore.QMetaType.QStringList)
        hint = {'urgency': self.URGENCY[level]}
        time = 5000   # milliseconds for display timeout

        bus = QtDBus.QDBusConnection.sessionBus()
        notify = QtDBus.QDBusInterface(item, path, interface, bus)
        if notify.isValid():
            x = notify.call(QtDBus.QDBus.AutoDetect, "Notify", app_name,
                            id_replace, icon, title, text,
                            actions_list, hint, time)
            if x.errorName():
                logger.warning("Failed to send notification!")
                logger.warning(x.errorMessage())
        else:
            logger.warning("Invalid dbus interface")

    def deliver(self, title, text, level='info'):
        if self.notifications_suppressed(level):
            return

        self._dbus_notify(title, text)
