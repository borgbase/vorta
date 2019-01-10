import sys
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
        import notify2

        self.NOTIFY2_LEVEL = {
            'info': notify2.URGENCY_NORMAL,
            'error': notify2.URGENCY_CRITICAL,
        }

        notify2.init('vorta')

    def deliver(self, title, text, level='info'):
        if self.notifications_suppressed(level):
            return

        import notify2
        n = notify2.Notification(title, text)
        n.set_urgency(self.NOTIFY2_LEVEL[level])
        return n.show()
