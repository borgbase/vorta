import sys
import pytest
from PyQt5 import QtDBus

import vorta.borg
import vorta.models
import vorta.notifications


@pytest.mark.skipif(sys.platform != 'linux', reason="DBus notifications only on Linux")
def test_linux_background_notifications(app, mocker):
    """We can't see notifications, but we watch for exceptions and errors."""

    notifier = vorta.notifications.VortaNotifications.pick()
    assert isinstance(notifier, vorta.notifications.DBusNotifications)
    notifier.deliver('Vorta Test', 'test notification', level='error')

    mocker.spy(QtDBus.QDBusInterface, 'call')
    notifier.deliver('Vorta Test', 'test notification', level='info')  # fails if called.
    assert QtDBus.QDBusInterface.call.call_count == 0
