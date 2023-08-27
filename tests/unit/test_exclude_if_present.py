from PyQt6 import QtCore


def test_exclusion_preview_populated(qapp, qtbot):
    main = qapp.main_window
    tab = main.sourceTab
    main.tabWidget.setCurrentIndex(1)

    qtbot.mouseClick(tab.bExcludeIfPresent, QtCore.Qt.MouseButton.LeftButton)
    qtbot.mouseClick(tab._window.bAddPattern, QtCore.Qt.MouseButton.LeftButton)

    qtbot.keyClicks(tab._window.customExclusionsList.viewport().focusWidget(), "custom pattern")
    qtbot.keyClick(tab._window.customExclusionsList.viewport().focusWidget(), QtCore.Qt.Key.Key_Enter)

    qtbot.waitUntil(
        lambda: tab._window.exclusionsPreviewText.toPlainText() == "# custom added rules\ncustom pattern\n\n"
    )

    tab._window.tabWidget.setCurrentIndex(2)

    qtbot.keyClicks(tab._window.rawExclusionsText, "test raw pattern 1")
    qtbot.waitUntil(lambda: "test raw pattern 1\n" in tab._window.exclusionsPreviewText.toPlainText())
