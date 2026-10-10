import pytest


def test_close_releases_native_window(qapp, qtbot, monkeypatch):
    """
    Closing the main window must release its native window (and with it the backing store),
    and showing it again must work as before.
    """
    main = qapp.main_window
    was_visible = main.isVisible()
    # Take the tray path in closeEvent(), also where no tray exists (headless CI).
    monkeypatch.setattr('vorta.views.main_window.is_system_tray_available', lambda: True)

    def shown():
        return main.isVisible() and main.windowHandle() is not None

    def released():
        return not main.isVisible() and main.windowHandle() is None

    qapp.open_main_window_action()
    qtbot.waitUntil(shown, **pytest._wait_defaults)

    main.close()
    qtbot.waitUntil(released, **pytest._wait_defaults)

    qapp.open_main_window_action()
    qtbot.waitUntil(shown, **pytest._wait_defaults)

    main.close()
    qtbot.waitUntil(released, **pytest._wait_defaults)

    # Leave the window as the other tests expect it.
    if was_visible:
        qapp.open_main_window_action()
        qtbot.waitUntil(shown, **pytest._wait_defaults)
