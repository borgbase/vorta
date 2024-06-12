from PyQt6 import QtCore


def test_exclusion_preview_populated(qapp, qtbot):
    main = qapp.main_window
    tab = main.sourceTab
    main.tabWidget.setCurrentIndex(1)

    qtbot.mouseClick(tab.bExclude, QtCore.Qt.MouseButton.LeftButton)
    qtbot.mouseClick(tab._window.bAddPattern, QtCore.Qt.MouseButton.LeftButton)

    qtbot.keyClicks(tab._window.customExclusionsList.viewport().focusWidget(), "custom pattern")
    qtbot.keyClick(tab._window.customExclusionsList.viewport().focusWidget(), QtCore.Qt.Key.Key_Enter)
    qtbot.waitUntil(lambda: "custom pattern" in tab._window.exclusionsPreviewText.toPlainText())

    tab._window.tabWidget.setCurrentIndex(1)

    tab._window.exclusionPresetsModel.itemFromIndex(tab._window.exclusionPresetsModel.index(0, 0)).setCheckState(
        QtCore.Qt.CheckState.Checked
    )

    qtbot.waitUntil(lambda: "# chromium-cache" in tab._window.exclusionsPreviewText.toPlainText())
    tab._window.tabWidget.setCurrentIndex(2)

    qtbot.keyClicks(tab._window.rawExclusionsText, "test raw pattern 1")
    qtbot.waitUntil(lambda: "test raw pattern 1\n" in tab._window.exclusionsPreviewText.toPlainText())

    qtbot.mouseClick(tab.bExclude, QtCore.Qt.MouseButton.LeftButton)
    qtbot.mouseClick(tab._window.bAddPatternExcludeIfPresent, QtCore.Qt.MouseButton.LeftButton)

    qtbot.keyClicks(tab._window.excludeIfPresentList.viewport().focusWidget(), "exclude_if_present_file")
    qtbot.keyClick(tab._window.excludeIfPresentList.viewport().focusWidget(), QtCore.Qt.Key.Key_Enter)
    qtbot.waitUntil(lambda: "exclude_if_present_file" in tab._window.exclusionsPreviewText.toPlainText())
