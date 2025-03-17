"""
Test backup creation
"""

import pytest
from PyQt6 import QtCore

# Import models to validate backup and logging results
from vorta.store.models import ArchiveModel, EventLogModel


def test_create(qapp, qtbot, archive_env):
    """
    Test for manual archive creation.

    This test simulates the process of initiating a backup through the UI,
    waits for the backup process to complete, and validates that the correct
    number of logs and archives have been created and displayed.
    """
    # Unpack the main window and archive tab from the test environment
    main, tab = archive_env

    # Simulate a user clicking the 'Start Backup' button
    qtbot.mouseClick(main.createStartBtn, QtCore.Qt.MouseButton.LeftButton)

    # Wait until the backup process indicates completion via the UI
    qtbot.waitUntil(lambda: 'Backup finished.' in main.progressText.text(), **pytest._wait_defaults)

    # Wait until the 'Start Backup' button is re-enabled (indicating readiness for next action)
    qtbot.waitUntil(lambda: main.createStartBtn.isEnabled(), **pytest._wait_defaults)

    # Validate that 2 event logs have been created (1 for start, 1 for completion)
    assert EventLogModel.select().count() == 2

    # Validate that the total number of archives is now 7 (assuming 6 pre-existing + 1 new)
    assert ArchiveModel.select().count() == 7

    # Check that the 'Start Backup' button is re-enabled post-backup
    assert main.createStartBtn.isEnabled()

    # Confirm that the archive table in the UI reflects 7 total archive entries
    assert main.archiveTab.archiveTable.rowCount() == 7

    # Confirm that the log page UI displays 2 log entries
    assert main.scheduleTab.logPage.logPage.rowCount() == 2
