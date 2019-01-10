import sys
from PyQt5 import QtCore, QtDBus
from vorta.models import SettingsModel


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
        elif sys.platform == 'linux':
            try:
                return LinuxNotifications()
            except ModuleNotFoundError:
                return cls()
        else:
            return cls()

    def deliver(self, title, text, level='info'):
        """Dummy notifier if we're not on macOS or Linux notifier isn't available."""
        pass

    def notifications_suppressed(self, level):
        """Decide if notification is sent or not based on settings and level."""
        if not SettingsModel.get(key='enable_notifications').value:
            return True
        if level == 'info' and not SettingsModel.get(key='enable_notifications_success').value:
            return True

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


class LinuxNotifications(VortaNotifications):
    """
    Use notify2 for emitting notifications on Linux.

    https://notify2.readthedocs.io/en/latest/
    Follows https://developer.gnome.org/notification-spec/
    """

    def __init__(self):
        pass

    def _dbus_notify(self, header, msg):
        item = "org.freedesktop.Notifications"
        path = "/org/freedesktop/Notifications"
        interface = "org.freedesktop.Notifications"
        app_name = "dbus_demo"
        v = QtCore.QVariant(12321)  # random int to identify all notifications
        if v.convert(QtCore.QVariant.UInt):
            id_replace = v
        icon = ""
        title = header
        text = msg
        actions_list = QtDBus.QDBusArgument([], QtCore.QMetaType.QStringList)
        hint = []
        time = 100   # milliseconds for display timeout

        bus = QtDBus.QDBusConnection.sessionBus()
        if not bus.isConnected():
            print("Not connected to dbus!")
        notify = QtDBus.QDBusInterface(item, path, interface, bus)
        if notify.isValid():
            x = notify.call(QtDBus.QDBus.AutoDetect, "Notify", app_name,
                            id_replace, icon, title, text,
                            actions_list, hint, time)
            if x.errorName():
                print("Failed to send notification!")
                print(x.errorMessage())
        else:
            print("Invalid dbus interface")

    def deliver(self, title, text, level='info'):
        if self.notifications_suppressed(level):
            return

        self.dbus_notify(title, text)
        # n.set_urgency(self.NOTIFY2_LEVEL[level])
        # return n.show()
