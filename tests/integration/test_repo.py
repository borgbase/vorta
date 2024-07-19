"""
Test backup creation
"""

import pytest
from PyQt6 import QtCore
from vorta.store.models import ArchiveModel, EventLogModel


def test_create(qapp, qtbot, archive_env):
    """Test for manual archive creation"""
    main, tab = archive_env

    qtbot.mouseClick(main.createStartBtn, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: 'Backup finished.' in main.progressText.text(), **pytest._wait_defaults)
    qtbot.waitUntil(lambda: main.createStartBtn.isEnabled(), **pytest._wait_defaults)

    assert EventLogModel.select().count() == 2
    assert ArchiveModel.select().count() == 7
    assert main.createStartBtn.isEnabled()
    assert main.archiveTab.archiveTable.rowCount() == 7
    assert main.scheduleTab.logPage.logPage.rowCount() == 2
