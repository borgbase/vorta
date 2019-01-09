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
            return DarwinNotifications
        elif sys.platform == 'linux':
            return LinuxNotifications
        else:  # Save to sqlite as fallback?
            return LinuxNotifications


class DarwinNotifications(VortaNotifications):

    def deliver(self, title, text, level='info'):
        if not SettingsModel.get(key='enable_notifications').value:
            return False
        if level == 'info' and not SettingsModel.get(key='enable_notifications_success').value:
            return False

        from Foundation import NSUserNotification
        from Foundation import NSUserNotificationCenter

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
    import notify2

    NOTIFY2_LEVEL = {
        'info': notify2.URGENCY_NORMAL,
        'error': notify2.URGENCY_CRITICAL,
    }

    def __init__(self):
        self.notify2.init('vorta')

    def deliver(self, title, text, level='info'):
        if not SettingsModel.get(key='enable_notifications').value:
            return False
        if level == 'info' and not SettingsModel.get(key='enable_notifications_success').value:
            return False

        n = self.notify2.Notification(title, text)
        n.set_urgency(self.NOTIFY2_LEVEL[level])
        return n.show()
