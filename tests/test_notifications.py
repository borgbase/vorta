import sys
import pytest

import vorta.borg
import vorta.models
import vorta.notifications


@pytest.mark.skipif(sys.platform != 'linux', reason="notify2 only on linux")
def test_linux_background_notifications(app, qtbot, mocker, borg_json_output):
    import notify2

    mocker.spy(notify2.Notification, 'show')

    notifier = vorta.notifications.VortaNotifications.pick()
    assert isinstance(notifier, vorta.notifications.LinuxNotifications)
    notifier.deliver('Vorta Test', 'test notification', level='error')
    notifier.deliver('Vorta Test', 'test notification', level='info')

    assert notify2.Notification.show.call_count == 2

