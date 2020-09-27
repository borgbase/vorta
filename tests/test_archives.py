import psutil
from collections import namedtuple
import pytest
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
    mocker.patch.object(vorta.borg.borg_thread, 'Popen', return_value=popen_result)

    main.tabWidget.setCurrentIndex(3)
    tab.list_action()
    qtbot.waitUntil(lambda: not tab.checkButton.isEnabled(), timeout=3000)

    assert not tab.checkButton.isEnabled()

    qtbot.waitUntil(lambda: main.progressText.text() == 'Refreshing archives done.', timeout=3000)
    assert ArchiveModel.select().count() == 6
    assert main.progressText.text() == 'Refreshing archives done.'
    assert tab.checkButton.isEnabled()


def test_repo_prune(qapp, qtbot, mocker, borg_json_output):
    main = qapp.main_window
    tab = main.archiveTab
    main.tabWidget.setCurrentIndex(3)
    tab.populate_from_profile()
    stdout, stderr = borg_json_output('prune')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_thread, 'Popen', return_value=popen_result)

    qtbot.mouseClick(tab.pruneButton, QtCore.Qt.LeftButton)

    qtbot.waitUntil(lambda: main.progressText.text().startswith('Refreshing archives done.'), timeout=5000)


def test_check(qapp, mocker, borg_json_output, qtbot):
    main = qapp.main_window
    tab = main.archiveTab
    main.tabWidget.setCurrentIndex(3)
    tab.populate_from_profile()

    stdout, stderr = borg_json_output('check')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_thread, 'Popen', return_value=popen_result)

    qtbot.mouseClick(tab.checkButton, QtCore.Qt.LeftButton)
    success_text = 'INFO: Archive consistency check complete'
    qtbot.waitUntil(lambda: main.logText.text().startswith(success_text), timeout=3000)


def test_archive_mount(qapp, qtbot, mocker, borg_json_output, monkeypatch, choose_file_dialog):
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

    stdout, stderr = borg_json_output('prune')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_thread, 'Popen', return_value=popen_result)

    monkeypatch.setattr(
        vorta.views.archive_tab, "choose_file_dialog", choose_file_dialog
    )

    qtbot.mouseClick(tab.mountButton, QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: tab.mountErrors.text().startswith('Mounted'), timeout=10000)

    qtbot.mouseClick(tab.mountButton, QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: tab.mountErrors.text().startswith('Un-mounted successfully.'), timeout=10000)


def test_archive_extract(qapp, qtbot, mocker, borg_json_output, monkeypatch):
    main = qapp.main_window
    tab = main.archiveTab
    main.tabWidget.setCurrentIndex(3)

    tab.populate_from_profile()
    qtbot.waitUntil(lambda: tab.archiveTable.rowCount() == 2)

    monkeypatch.setattr(
        vorta.views.extract_dialog.ExtractDialog, "exec_", lambda *args: True
    )

    tab.archiveTable.selectRow(0)
    stdout, stderr = borg_json_output('list_archive')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_thread, 'Popen', return_value=popen_result)
    qtbot.mouseClick(tab.extractButton, QtCore.Qt.LeftButton)

    qtbot.waitUntil(lambda: hasattr(tab, '_window'), timeout=10000)

    assert tab._window.treeView.model().rootItem.childItems[0].data(0) == 'Users'
    tab._window.treeView.model().rootItem.childItems[0].load_children()
    assert tab._window.archiveNameLabel.text().startswith('test-archive, 2000')


def test_archive_diff(qapp, qtbot, mocker, borg_json_output, monkeypatch):
    main = qapp.main_window
    tab = main.archiveTab
    main.tabWidget.setCurrentIndex(3)

    tab.populate_from_profile()
    qtbot.waitUntil(lambda: tab.archiveTable.rowCount() == 2)

    monkeypatch.setattr(
        vorta.views.diff_dialog.DiffDialog, "exec_", lambda *args: True
    )

    monkeypatch.setattr(
        tab, "selected_archives", (0, 1)
    )

    stdout, stderr = borg_json_output('diff_archives')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_thread, 'Popen', return_value=popen_result)

    qtbot.mouseClick(tab.diffButton, QtCore.Qt.LeftButton)
    qtbot.waitUntil(lambda: hasattr(tab, '_window'), timeout=5000)

    monkeypatch.setattr(
        vorta.views.diff_result.DiffResult, "exec_", lambda *args: True
    )
    qtbot.waitUntil(lambda: hasattr(tab, '_resultwindow'), timeout=5000)

    assert tab._resultwindow.treeView.model().rootItem.childItems[0].data(0) == 'test'
    tab._resultwindow.treeView.model().rootItem.childItems[0].load_children()

    assert tab._resultwindow.archiveNameLabel_1.text() == 'test-archive'
    tab._resultwindow.accept()


@pytest.mark.parametrize('line, expected', [
    ('changed link        some/changed/link',
     (0, 'changed', 'link', 'some/changed')),
    (' +77.8 kB  -77.8 kB some/changed/file',
     (77800, 'modified', 'file', 'some/changed')),
    (' +77.8 kB  -77.8 kB [-rw-rw-rw- -> -rw-r--r--] some/changed/file',
     (77800, '[-rw-rw-rw- -> -rw-r--r--]', 'file', 'some/changed')),
    ('[-rw-rw-rw- -> -rw-r--r--] some/changed/file',
     (0, '[-rw-rw-rw- -> -rw-r--r--]', 'file', 'some/changed')),

    ('added directory    some/changed/dir',
     (0, 'added', 'dir', 'some/changed')),
    ('removed directory  some/changed/dir',
     (0, 'removed', 'dir', 'some/changed')),

    # Example from https://github.com/borgbase/vorta/issues/521
    ('[user:user -> nfsnobody:nfsnobody] home/user/arrays/test.txt',
     (0, 'modified', 'test.txt', 'home/user/arrays')),

    # Very short owner change, to check stripping whitespace from file path
    ('[a:a -> b:b]       home/user/arrays/test.txt',
     (0, 'modified', 'test.txt', 'home/user/arrays')),

    # All file-related changes in one test
    (' +77.8 kB  -77.8 kB [user:user -> nfsnobody:nfsnobody] [-rw-rw-rw- -> -rw-r--r--] home/user/arrays/test.txt',
     (77800, '[-rw-rw-rw- -> -rw-r--r--]', 'test.txt', 'home/user/arrays')),
])
def test_archive_diff_parser(line, expected):
    files_with_attributes, nested_file_list = vorta.views.diff_result.parse_diff_lines([line])
    assert files_with_attributes == [expected]
