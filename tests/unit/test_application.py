import sys

import pytest


@pytest.mark.skipif(sys.platform != 'darwin', reason='macOS activation policy only')
def test_runs_as_accessory_app(qapp):
    """A plain `vorta` run must use the bundle's LSUIElement policy, or macOS quits it after the last window closes."""
    from AppKit import NSApp, NSApplicationActivationPolicyAccessory

    assert NSApp.activationPolicy() == NSApplicationActivationPolicyAccessory
