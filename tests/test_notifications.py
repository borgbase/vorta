import sys
import pytest

import vorta.borg
import vorta.models
import vorta.notifications


@pytest.mark.skipif(sys.platform != 'linux', reason="notify2 only on linux")
def test_linux_background_notifications(app, qtbot, mocker, borg_json_output):
    mocker.spy(vorta.notifications.LinuxNotifications, 'deliver')

    notifier = vorta.notifications.VortaNotifications.pick()
    result_err = notifier.deliver('Vorta Test', 'test notification', level='error')
    result_info = notifier.deliver('Vorta Test', 'test notification', level='info')

    assert vorta.notifications.LinuxNotifications.deliver.call_count == 2
    assert result_err is True
    assert result_info is False
