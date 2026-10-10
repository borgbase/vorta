import sys
from unittest.mock import MagicMock

import pytest

from vorta.updater import get_updater


@pytest.mark.skipif(sys.platform != 'darwin', reason='The Sparkle updater is macOS only.')
def test_get_updater_loads_sparkle_without_class_scan(qapp, monkeypatch):
    """
    Sparkle must be loaded without PyObjC's class scan.

    The scan wraps every Objective-C class in the process as a Python class and keeps them
    in the module globals, which costs well over 100 MB for the lifetime of the app.
    """
    import objc

    load_bundle = MagicMock()
    look_up_class = MagicMock()
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(objc, 'loadBundle', load_bundle)
    monkeypatch.setattr(objc, 'lookUpClass', look_up_class)

    updater = get_updater()

    load_bundle.assert_called_once()
    assert load_bundle.call_args.kwargs['scan_classes'] is False
    look_up_class.assert_called_once_with('SUUpdater')
    assert updater is look_up_class.return_value.sharedUpdater.return_value
