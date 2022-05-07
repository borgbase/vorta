from collections import namedtuple

import psutil
import pytest
from PyQt5 import QtCore

import vorta.borg
import vorta.utils
import vorta.views.archive_tab
from vorta.store.models import ArchiveModel, BackupProfileModel


class MockFileDialog:
    def open(self, func):
        func()

    def selectedFiles(self):
        return ['/tmp']


def test_prune_intervals(qapp, qtbot):
    prune_intervals = ['hour', 'day', 'week', 'month', 'year']
    main = qapp.main_window
    tab = main.archiveTab
    profile = BackupProfileModel.get(id=1)

    for i in prune_intervals:
        getattr(tab, f'prune_{i}').setValue(9)
        tab.save_prune_setting(None)
        profile = profile.refresh()
        assert getattr(profile, f'prune_{i}') == 9


def test_repo_list(qapp, qtbot, mocker, borg_json_output):
    main = qapp.main_window
    tab = main.archiveTab

    stdout, stderr = borg_json_output('list')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    main.tabWidget.setCurrentIndex(3)
    tab.refresh_archive_list()
    qtbot.waitUntil(lambda: not tab.bCheck.isEnabled(), **pytest._wait_defaults)

    assert not tab.bCheck.isEnabled()

    qtbot.waitUntil(lambda: main.progressText.text() == 'Refreshing archives done.', **pytest._wait_defaults)
    assert ArchiveModel.select().count() == 6
    assert main.progressText.text() == 'Refreshing archives done.'
    assert tab.bCheck.isEnabled()


def test_repo_prune(qapp, qtbot, mocker, borg_json_output):
    main = qapp.main_window
    tab = main.archiveTab
    main.tabWidget.setCurrentIndex(3)
    tab.populate_from_profile()
    stdout, stderr = borg_json_output('prune')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    qtbot.mouseClick(tab.bPrune, QtCore.Qt.LeftButton)

    qtbot.waitUntil(lambda: main.progressText.text().startswith('Refreshing archives done.'), **pytest._wait_defaults)


def test_repo_compact(qapp, qtbot, mocker, borg_json_output):
    main = qapp.main_window
    tab = main.archiveTab
    vorta.utils.borg_compat.version = '1.2.0'
    main.tabWidget.setCurrentIndex(3)
    tab.populate_from_profile()
    stdout, stderr = borg_json_output('compact')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    qtbot.mouseClick(tab.compactButton, QtCore.Qt.LeftButton)

    qtbot.waitUntil(
        lambda: 'compaction freed about 56.00 kB repository space' in main.logText.text(),
        **pytest._wait_defaults
    )
    vorta.utils.borg_compat.version = '1.1.0'


def test_check(qapp, mocker, borg_json_output, qtbot):
    main = qapp.main_window
    tab = main.archiveTab
    main.tabWidget.setCurrentIndex(3)
    tab.populate_from_profile()

    stdout, stderr = borg_json_output('check')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    qtbot.mouseClick(tab.bCheck, QtCore.Qt.LeftButton)
    success_text = 'INFO: Archive consistency check complete'
    qtbot.waitUntil(lambda: main.logText.text().startswith(success_text), **pytest._wait_defaults)


def test_mount(qapp, qtbot, mocker, borg_json_output, monkeypatch, choose_file_dialog):
    def psutil_disk_partitions(**kwargs):
        DiskPartitions = namedtuple('DiskPartitions', ['device', 'mountpoint'])
        return [DiskPartitions('borgfs', '/tmp')]

    monkeypatch.setattr(
        psutil, "disk_partitions", psutil_disk_partitions
    )

    main = qapp.main_window
    tab = main.archiveTab
    main.tabWidget.setCurrentIndex(3)
    tab.populate_from_profile()
    tab.archiveTable.selectRow(0)

    stdout, stderr = borg_json_output('prune')  # TODO: fully mock mount command?
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    monkeypatch.setattr(
        vorta.views.archive_tab, "choose_file_dialog", choose_file_dialog
    )

    tab.bmountarchive_clicked()
    qtbot.waitUntil(lambda: tab.mountErrors.text().startswith('Mounted'), **pytest._wait_defaults)

    tab.bmountarchive_clicked()
    qtbot.waitUntil(lambda: tab.mountErrors.text().startswith('Un-mounted successfully.'), **pytest._wait_defaults)

    tab.bmountrepo_clicked()
    qtbot.waitUntil(lambda: tab.mountErrors.text().startswith('Mounted'), **pytest._wait_defaults)

    tab.bmountrepo_clicked()
    qtbot.waitUntil(lambda: tab.mountErrors.text().startswith('Un-mounted successfully.'), **pytest._wait_defaults)


def test_archive_extract(qapp, qtbot, mocker, borg_json_output):
    main = qapp.main_window
    tab = main.archiveTab
    main.tabWidget.setCurrentIndex(3)

    tab.populate_from_profile()
    qtbot.waitUntil(lambda: tab.archiveTable.rowCount() == 2)

    tab.archiveTable.selectRow(0)
    stdout, stderr = borg_json_output('list_archive')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)
    tab.extract_action()

    qtbot.waitUntil(lambda: hasattr(tab, '_window'), **pytest._wait_defaults)
    # qtbot.waitUntil(lambda: tab._window == qapp.activeWindow(), **pytest._wait_defaults)

    model = tab._window.model
    assert model.root.children[0].subpath == 'home'
    assert tab._window.archiveNameLabel.text().startswith('test-archive, 2000')


def test_archive_delete(qapp, qtbot, mocker, borg_json_output):
    main = qapp.main_window
    tab = main.archiveTab
    main.tabWidget.setCurrentIndex(3)

    tab.populate_from_profile()
    qtbot.waitUntil(lambda: tab.archiveTable.rowCount() == 2)

    tab.archiveTable.selectRow(0)
    stdout, stderr = borg_json_output('delete')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)
    mocker.patch.object(vorta.views.archive_tab.ArchiveTab, 'confirm_dialog', lambda x, y, z: True)
    tab.delete_action()

    qtbot.waitUntil(lambda: main.progressText.text() == 'Archive deleted.', **pytest._wait_defaults)
    assert ArchiveModel.select().count() == 1
    assert tab.archiveTable.rowCount() == 1


def test_archive_rename(qapp, qtbot, mocker, borg_json_output):
    main = qapp.main_window
    tab = main.archiveTab
    main.tabWidget.setCurrentIndex(3)

    tab.populate_from_profile()
    qtbot.waitUntil(lambda: tab.archiveTable.rowCount() == 2)

    tab.archiveTable.selectRow(0)
    new_archive_name = 'idf89d8f9d8fd98'
    stdout, stderr = borg_json_output('rename')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)
    mocker.patch.object(vorta.views.archive_tab.QInputDialog, 'getText', return_value=(new_archive_name, True))
    tab.rename_action()

    # Successful rename case
    qtbot.waitUntil(lambda: tab.mountErrors.text() == 'Archive renamed.', **pytest._wait_defaults)
    assert ArchiveModel.select().filter(name=new_archive_name).count() == 1

    # Duplicate name case
    tab.archiveTable.selectRow(0)
    exp_text = 'An archive with this name already exists.'
    mocker.patch.object(vorta.views.archive_tab.QInputDialog, 'getText', return_value=(new_archive_name, True))
    tab.rename_action()
    qtbot.waitUntil(lambda: tab.mountErrors.text() == exp_text, **pytest._wait_defaults)
