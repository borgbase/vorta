"""
This file contains tests for the Archive tab to test the various archive related borg commands.
"""

import sys
from collections import namedtuple

import psutil
import pytest
import vorta.borg
import vorta.utils
import vorta.views.archive_tab
from PyQt6 import QtCore
from vorta.store.models import ArchiveModel


def test_repo_list(qapp, qtbot):
    """Test that the archives are created and repo list is populated correctly"""
    main = qapp.main_window
    tab = main.archiveTab

    main.tabWidget.setCurrentIndex(3)
    tab.refresh_archive_list()
    qtbot.waitUntil(lambda: not tab.bCheck.isEnabled(), **pytest._wait_defaults)

    assert not tab.bCheck.isEnabled()

    qtbot.waitUntil(lambda: 'Refreshing archives done.' in main.progressText.text(), **pytest._wait_defaults)
    assert ArchiveModel.select().count() == 6
    assert 'Refreshing archives done.' in main.progressText.text()
    assert tab.bCheck.isEnabled()


def test_repo_prune(qapp, qtbot):
    """Test for archive pruning"""
    main = qapp.main_window
    tab = main.archiveTab

    main.tabWidget.setCurrentIndex(3)
    tab.refresh_archive_list()
    qtbot.waitUntil(lambda: tab.archiveTable.rowCount() > 0, **pytest._wait_defaults)

    qtbot.mouseClick(tab.bPrune, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: 'Pruning old archives' in main.progressText.text(), **pytest._wait_defaults)
    qtbot.waitUntil(lambda: 'Refreshing archives done.' in main.progressText.text(), **pytest._wait_defaults)


@pytest.mark.min_borg_version('1.2.0a1')
def test_repo_compact(qapp, qtbot):
    """Test for archive compaction"""
    main = qapp.main_window
    tab = main.archiveTab

    main.tabWidget.setCurrentIndex(3)
    tab.refresh_archive_list()
    qtbot.waitUntil(lambda: tab.archiveTable.rowCount() > 0, **pytest._wait_defaults)

    qtbot.waitUntil(lambda: tab.compactButton.isEnabled(), **pytest._wait_defaults)
    assert tab.compactButton.isEnabled()

    qtbot.mouseClick(tab.compactButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: 'compaction freed about' in main.logText.text().lower(), **pytest._wait_defaults)


def test_check(qapp, qtbot):
    """Test for archive consistency check"""
    main = qapp.main_window
    tab = main.archiveTab

    main.tabWidget.setCurrentIndex(3)
    tab.refresh_archive_list()
    qtbot.waitUntil(lambda: tab.archiveTable.rowCount() > 0, **pytest._wait_defaults)

    qapp.check_failed_event.disconnect()

    qtbot.waitUntil(lambda: tab.bCheck.isEnabled(), **pytest._wait_defaults)
    qtbot.mouseClick(tab.bCheck, QtCore.Qt.MouseButton.LeftButton)
    success_text = 'INFO: Archive consistency check complete'

    qtbot.waitUntil(lambda: success_text in main.logText.text(), **pytest._wait_defaults)


@pytest.mark.skipif(sys.platform == 'darwin', reason="Macos fuse support is uncertain")
def test_mount(qapp, qtbot, monkeypatch, choose_file_dialog, tmpdir):
    """Test for archive mounting and unmounting"""

    def psutil_disk_partitions(**kwargs):
        DiskPartitions = namedtuple('DiskPartitions', ['device', 'mountpoint'])
        return [DiskPartitions('borgfs', str(tmpdir))]

    monkeypatch.setattr(psutil, "disk_partitions", psutil_disk_partitions)
    monkeypatch.setattr(vorta.views.archive_tab, "choose_file_dialog", choose_file_dialog)

    main = qapp.main_window
    tab = main.archiveTab

    main.tabWidget.setCurrentIndex(3)
    tab.refresh_archive_list()
    qtbot.waitUntil(lambda: tab.archiveTable.rowCount() > 0, **pytest._wait_defaults)
    tab.archiveTable.selectRow(0)

    qtbot.waitUntil(lambda: tab.bMountRepo.isEnabled(), **pytest._wait_defaults)

    qtbot.mouseClick(tab.bMountArchive, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: tab.mountErrors.text().startswith('Mounted'), **pytest._wait_defaults)

    tab.bmountarchive_clicked()
    qtbot.waitUntil(lambda: tab.mountErrors.text().startswith('Un-mounted successfully.'), **pytest._wait_defaults)

    tab.bmountrepo_clicked()
    qtbot.waitUntil(lambda: tab.mountErrors.text().startswith('Mounted'), **pytest._wait_defaults)

    tab.bmountrepo_clicked()
    qtbot.waitUntil(lambda: tab.mountErrors.text().startswith('Un-mounted successfully.'), **pytest._wait_defaults)


def test_archive_extract(qapp, qtbot, monkeypatch, choose_file_dialog, tmpdir):
    """Test for archive extraction"""
    main = qapp.main_window
    tab = main.archiveTab

    main.tabWidget.setCurrentIndex(3)
    tab.refresh_archive_list()
    qtbot.waitUntil(lambda: tab.archiveTable.rowCount() > 0, **pytest._wait_defaults)

    tab.archiveTable.selectRow(2)
    tab.extract_action()

    qtbot.waitUntil(lambda: hasattr(tab, '_window'), **pytest._wait_defaults)

    # Select all files
    tree_view = tab._window.treeView.model()
    tree_view.setData(tree_view.index(0, 0), QtCore.Qt.CheckState.Checked, QtCore.Qt.ItemDataRole.CheckStateRole)
    monkeypatch.setattr(vorta.views.archive_tab, "choose_file_dialog", choose_file_dialog)
    qtbot.mouseClick(tab._window.extractButton, QtCore.Qt.MouseButton.LeftButton)

    qtbot.waitUntil(lambda: 'Restored files from archive.' in main.progressText.text(), **pytest._wait_defaults)

    assert [item.basename for item in tmpdir.listdir()] == ['private' if sys.platform == 'darwin' else 'tmp']


def test_archive_delete(qapp, qtbot, mocker):
    """Test for archive deletion"""
    main = qapp.main_window
    tab = main.archiveTab

    main.tabWidget.setCurrentIndex(3)
    tab.refresh_archive_list()
    qtbot.waitUntil(lambda: tab.archiveTable.rowCount() > 0, **pytest._wait_defaults)

    archivesCount = tab.archiveTable.rowCount()

    mocker.patch.object(vorta.views.archive_tab.ArchiveTab, 'confirm_dialog', lambda x, y, z: True)

    tab.archiveTable.selectRow(0)
    tab.delete_action()
    qtbot.waitUntil(lambda: 'Archive deleted.' in main.progressText.text(), **pytest._wait_defaults)

    assert ArchiveModel.select().count() == archivesCount - 1
    assert tab.archiveTable.rowCount() == archivesCount - 1


def test_archive_rename(qapp, qtbot, mocker):
    """Test for archive renaming"""
    main = qapp.main_window
    tab = main.archiveTab

    main.tabWidget.setCurrentIndex(3)
    tab.refresh_archive_list()
    qtbot.waitUntil(lambda: tab.archiveTable.rowCount() > 0, **pytest._wait_defaults)

    tab.archiveTable.selectRow(0)
    new_archive_name = 'idf89d8f9d8fd98'
    mocker.patch.object(vorta.views.archive_tab.QInputDialog, 'getText', return_value=(new_archive_name, True))
    tab.rename_action()

    # Successful rename case
    qtbot.waitUntil(lambda: tab.mountErrors.text() == 'Archive renamed.', **pytest._wait_defaults)
    assert ArchiveModel.select().filter(name=new_archive_name).count() == 1

    # Duplicate name case
    tab.archiveTable.selectRow(0)
    exp_text = 'An archive with this name already exists.'
    tab.rename_action()
    qtbot.waitUntil(lambda: tab.mountErrors.text() == exp_text, **pytest._wait_defaults)
