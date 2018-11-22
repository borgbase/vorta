import sys


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
    def deliver(self, title, text):
        from Foundation import NSUserNotification
        from Foundation import NSUserNotificationCenter

        notification = NSUserNotification.alloc().init()
        notification.setTitle_(title)
        notification.setInformativeText_(text)
        center = NSUserNotificationCenter.defaultUserNotificationCenter()
        if center is not None:  # Only works when run from app bundle.
            center.deliverNotification_(notification)


class LinuxNotifications(VortaNotifications):
    """
    Could use the Gnome libs or the binary

    https://wiki.archlinux.org/index.php/Desktop_notifications#Python
    http://manpages.ubuntu.com/manpages/cosmic/man1/notify-send.1.html
    """
    def deliver(self, title, text):
        pass
