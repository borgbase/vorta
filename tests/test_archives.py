import psutil
from collections import namedtuple
from PyQt5 import QtCore
from vorta.models import BackupProfileModel, ArchiveModel
import vorta.borg
import vorta.views.archive_tab
import vorta.utils


class MockFileDialog:
    def open(self, func):
        func()

    def selectedFiles(self):
        return ['/tmp']


def test_prune_intervals(app, qtbot):
    prune_intervals = ['hour', 'day', 'week', 'month', 'year']
    main = app.main_window
    tab = main.archiveTab
    profile = BackupProfileModel.get(id=1)

    for i in prune_intervals:
        getattr(tab, f'prune_{i}').setValue(9)
        tab.save_prune_setting(None)
        profile = profile.refresh()
        assert getattr(profile, f'prune_{i}') == 9


def test_repo_list(app, qtbot, mocker, borg_json_output):
    main = app.main_window
    tab = main.archiveTab
    main.tabWidget.setCurrentIndex(3)
    tab.list_action()
    assert not tab.checkButton.isEnabled()

    stdout, stderr = borg_json_output('list')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_thread, 'Popen', return_value=popen_result)

    qtbot.waitUntil(lambda: main.createProgressText.text() == 'Refreshing snapshots done.', timeout=3000)
    assert ArchiveModel.select().count() == 6
    assert main.createProgressText.text() == 'Refreshing snapshots done.'
    assert tab.checkButton.isEnabled()


def test_repo_prune(app, qtbot, mocker, borg_json_output):
    main = app.main_window
    tab = main.archiveTab
    main.tabWidget.setCurrentIndex(3)
    tab.populate_from_profile()
    stdout, stderr = borg_json_output('prune')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_thread, 'Popen', return_value=popen_result)

    qtbot.mouseClick(tab.pruneButton, QtCore.Qt.LeftButton)

    qtbot.waitUntil(lambda: main.createProgressText.text().startswith('Refreshing snapshots'), timeout=5000)


def test_check(app, mocker, borg_json_output, qtbot):
    main = app.main_window
    tab = main.archiveTab
    main.tabWidget.setCurrentIndex(3)
    tab.populate_from_profile()

    stdout, stderr = borg_json_output('check')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_thread, 'Popen', return_value=popen_result)

    qtbot.mouseClick(tab.checkButton, QtCore.Qt.LeftButton)
    success_text = 'INFO: Archive consistency check complete'
    qtbot.waitUntil(lambda: main.createProgressText.text().startswith(success_text), timeout=3000)


def test_archive_mount(app, qtbot, mocker, borg_json_output, monkeypatch, choose_file_dialog):
    def psutil_disk_partitions(**kwargs):
        DiskPartitions = namedtuple('DiskPartitions', ['device', 'mountpoint'])
        return [DiskPartitions('borgfs', '/tmp')]

    monkeypatch.setattr(
        psutil, "disk_partitions", psutil_disk_partitions
    )

    main = app.main_window
    tab = main.archiveTab
    main.tabWidget.setCurrentIndex(3)
    tab.populate_from_profile()
    tab.archiveTable.selectRow(0)

    stdout, stderr = borg_json_output('prune')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_thread, 'Popen', return_value=popen_result)

    monkeypatch.setattr(
        vorta.views.archive_tab, "choose_file_dialog", choose_file_dialog
    )

    qtbot.mouseClick(tab.mountButton, QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: tab.mountErrors.text().startswith('Mounted'), timeout=5000)

    qtbot.mouseClick(tab.mountButton, QtCore.Qt.LeftButton)
    # qtbot.waitUntil(lambda: tab.mountErrors.text() == 'No active Borg mounts found.')

    qtbot.waitUntil(lambda: tab.mountErrors.text().startswith('Un-mounted successfully.'), timeout=5000)


def test_archive_extract(app, qtbot, mocker, borg_json_output, monkeypatch):
    main = app.main_window
    tab = main.archiveTab
    main.tabWidget.setCurrentIndex(3)

    tab.populate_from_profile()
    qtbot.waitUntil(lambda: tab.archiveTable.rowCount() == 1)

    qtbot.mouseClick(tab.extractButton, QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: tab.mountErrors.text().startswith('Select an archive'))

    monkeypatch.setattr(
        vorta.views.extract_dialog.ExtractDialog, "exec_", lambda *args: True
    )

    tab.archiveTable.selectRow(0)
    stdout, stderr = borg_json_output('list_archive')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_thread, 'Popen', return_value=popen_result)
    qtbot.mouseClick(tab.extractButton, QtCore.Qt.LeftButton)

    qtbot.waitUntil(lambda: hasattr(tab, '_window'), timeout=5000)

    assert tab._window.treeView.model().rootItem.childItems[0].data(0) == 'Users'
    tab._window.treeView.model().rootItem.childItems[0].load_children()

    assert tab._window.archiveNameLabel.text().startswith('test-archive, 2000')
    tab._window.accept()
