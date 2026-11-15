"""
This file contains tests for the Archive tab to test the various archive related borg commands.
"""

import subprocess
import sys
from collections import namedtuple
from pathlib import Path

import psutil
import pytest
from packaging.version import Version
from PyQt6 import QtCore
from PyQt6.QtCore import QDateTime

import vorta.borg
import vorta.utils
import vorta.views.archive.archive_extract
import vorta.views.archive_tab
from vorta.borg.extract import BorgExtractJob, _include_pattern
from vorta.store.models import ArchiveModel, BackupProfileModel
from vorta.views.dialogs.archive.extract import ExtractTree, FileData, FileType, parse_json_lines
from vorta.views.partials.treemodel import FileSystemItem


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


def test_repo_prune(qapp, qtbot, archive_env):
    """Test for archive pruning"""
    main, tab = archive_env
    qtbot.mouseClick(tab.bPrune, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: 'Pruning old archives' in main.progressText.text(), **pytest._wait_defaults)
    qtbot.waitUntil(lambda: 'Refreshing archives done.' in main.progressText.text(), **pytest._wait_defaults)


@pytest.mark.min_borg_version('1.2.0a1')
def test_repo_compact(qapp, qtbot, archive_env):
    """Test for archive compaction"""
    main, tab = archive_env
    qtbot.waitUntil(lambda: tab.compactButton.isEnabled(), **pytest._wait_defaults)
    assert tab.compactButton.isEnabled()

    qtbot.mouseClick(tab.compactButton, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: 'compaction freed about' in main.logText.text().lower(), **pytest._wait_defaults)


def test_check(qapp, qtbot, archive_env):
    """Test for archive consistency check"""
    main, tab = archive_env

    qapp.check_failed_event.disconnect()

    qtbot.waitUntil(lambda: tab.bCheck.isEnabled(), **pytest._wait_defaults)
    qtbot.mouseClick(tab.bCheck, QtCore.Qt.MouseButton.LeftButton)
    success_text = 'INFO: Archive consistency check complete'

    qtbot.waitUntil(lambda: success_text in main.logText.text(), **pytest._wait_defaults)


@pytest.mark.skipif(sys.platform == 'darwin', reason="Macos fuse support is uncertain")
def test_mount(qapp, qtbot, monkeypatch, choose_file_dialog, tmpdir, archive_env):
    """Test for archive mounting and unmounting"""

    def psutil_disk_partitions(**kwargs):
        DiskPartitions = namedtuple('DiskPartitions', ['device', 'mountpoint'])
        return [DiskPartitions('borgfs', str(tmpdir))]

    monkeypatch.setattr(psutil, "disk_partitions", psutil_disk_partitions)
    monkeypatch.setattr("vorta.views.archive.archive_mount.choose_file_dialog", choose_file_dialog)

    main, tab = archive_env
    tab.archiveTable.selectRow(0)

    qtbot.waitUntil(lambda: tab.bMountRepo.isEnabled(), **pytest._wait_defaults)

    qtbot.mouseClick(tab.bMountArchive, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: tab.mountErrors.text().startswith('Mounted'), **pytest._wait_defaults)

    tab.archive_mount.bmountarchive_clicked()
    qtbot.waitUntil(lambda: tab.mountErrors.text().startswith('Un-mounted successfully.'), **pytest._wait_defaults)

    tab.archive_mount.bmountrepo_clicked()
    qtbot.waitUntil(lambda: tab.mountErrors.text().startswith('Mounted'), **pytest._wait_defaults)

    tab.archive_mount.bmountrepo_clicked()
    qtbot.waitUntil(lambda: tab.mountErrors.text().startswith('Un-mounted successfully.'), **pytest._wait_defaults)


def test_archive_extract(qapp, qtbot, monkeypatch, choose_file_dialog, tmpdir, archive_env):
    """Test for archive extraction"""
    main, tab = archive_env

    tab.archiveTable.selectRow(2)
    tab.archive_extract.extract_action()

    qtbot.waitUntil(lambda: hasattr(tab, '_window'), **pytest._wait_defaults)

    # Select all files
    tree_view = tab._window.treeView.model()
    tree_view.setData(tree_view.index(0, 0), QtCore.Qt.CheckState.Checked, QtCore.Qt.ItemDataRole.CheckStateRole)
    monkeypatch.setattr(vorta.views.archive.archive_extract, "choose_file_dialog", choose_file_dialog)
    qtbot.mouseClick(tab._window.extractButton, QtCore.Qt.MouseButton.LeftButton)

    qtbot.waitUntil(lambda: 'Restored files from archive.' in main.progressText.text(), **pytest._wait_defaults)

    assert [item.basename for item in tmpdir.listdir()] == ['private' if sys.platform == 'darwin' else 'tmp']


@pytest.mark.parametrize(
    'selected_paths, expected_patterns, expected_files',
    [
        (
            [('root', 'keep'), ('root', 'other', 'nested', 'target')],
            {'+ pp:root/keep', '+ pf:root/other/nested/target'},
            {'root/keep/one', 'root/keep/two', 'root/other/nested/target'},
        ),
        (
            [('root', 'other', 'nested', 'target')],
            {'+ pf:root/other/nested/target'},
            {'root/other/nested/target'},
        ),
    ],
)
def test_extract_selected_patterns(
    qapp, tmpdir, create_test_repo, borg_version, selected_paths, expected_patterns, expected_files
):
    """Borg restores selected directories and files without similarly named siblings."""
    repo = create_test_repo[0]
    source = tmpdir.mkdir('pattern_source')
    root = source.mkdir('root')
    keep = root.mkdir('keep')
    keep.join('one').write('one')
    keep.join('two').write('two')
    root.mkdir('keep-extra').join('other').write('other')
    nested = root.mkdir('other').mkdir('nested')
    nested.join('target').write('target')
    nested.join('target.bak').write('target.bak')

    archive_name = 'selection-patterns'
    is_borg_v2 = borg_version[1] >= Version('2.0.0b1')
    if is_borg_v2:
        create_cmd = ['borg', '-r', str(repo), 'create', archive_name, 'root']
    else:
        create_cmd = ['borg', 'create', f'{repo}::{archive_name}', 'root']
    subprocess.run(create_cmd, cwd=str(source), check=True)

    paths = [
        ('root', 'd'),
        ('root/keep', 'd'),
        ('root/keep/one', '-'),
        ('root/keep/two', '-'),
        ('root/keep-extra', 'd'),
        ('root/keep-extra/other', '-'),
        ('root/other', 'd'),
        ('root/other/nested', 'd'),
        ('root/other/nested/target', '-'),
        ('root/other/nested/target.bak', '-'),
    ]
    model = ExtractTree()
    parse_json_lines([{'path': path, 'mode': mode} for path, mode in paths], model)
    for path in selected_paths:
        model.setData(model.indexPath(path), QtCore.Qt.CheckState.Checked, QtCore.Qt.ItemDataRole.CheckStateRole)

    destination = tmpdir.mkdir('pattern_destination')
    prepared = BorgExtractJob.prepare(BackupProfileModel.get(), archive_name, model, str(destination))
    assert prepared['ok']
    pattern_lines = Path(prepared['cleanup_files'][0].name).read_text().splitlines()
    assert pattern_lines[0] == 'P pp'
    assert pattern_lines[-1] == '- fm:*'
    assert set(pattern_lines[1:-1]) == expected_patterns

    subprocess.run(prepared['cmd'], cwd=prepared['cwd'], check=True, capture_output=True)
    restored_files = {
        str(path.relative_to(str(destination))) for path in Path(str(destination)).rglob('*') if path.is_file()
    }
    assert restored_files == expected_files


def test_archive_delete(qapp, qtbot, mocker, archive_env):
    """Test for archive deletion"""
    main, tab = archive_env

    archivesCount = tab.archiveTable.model().rowCount()

    mocker.patch.object(vorta.views.archive_tab.ArchiveTab, 'confirm_dialog', lambda x, y, z: True)

    tab.archiveTable.selectRow(0)
    tab.archive_delete.delete_action()
    qtbot.waitUntil(lambda: 'Archive deleted.' in main.progressText.text(), **pytest._wait_defaults)

    assert ArchiveModel.select().count() == archivesCount - 1
    assert tab.archiveTable.model().rowCount() == archivesCount - 1


def test_archive_rename(qapp, qtbot, mocker, archive_env):
    """Test for archive renaming"""
    main, tab = archive_env

    tab.archiveTable.selectRow(0)
    new_archive_name = 'idf89d8f9d8fd98'
    pos = tab.archiveTable.visualRect(tab.archiveTable.model().index(0, 4)).center()
    qtbot.mouseClick(tab.archiveTable.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=pos)
    qtbot.mouseDClick(tab.archiveTable.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=pos)
    qtbot.keyClicks(tab.archiveTable.viewport().focusWidget(), new_archive_name)
    qtbot.keyClick(tab.archiveTable.viewport().focusWidget(), QtCore.Qt.Key.Key_Return)

    # Successful rename case
    qtbot.waitUntil(lambda: tab.archiveTable.model().index(0, 4).data() == new_archive_name, **pytest._wait_defaults)


def test_extract_unsafe_filenames(tmpdir, borg_version):
    """Files with line breaks or edge whitespace in their name can be restored via a pattern file."""
    is_borg_v2 = borg_version[1] >= Version('2.0.0b1')
    repo = tmpdir.mkdir('repo')
    src = tmpdir.mkdir('src')
    dest = tmpdir.mkdir('dest')

    wanted = ['a\nPRIMARY b', 'c\r\nd', 'trailing ']
    for name in wanted + ['other']:
        src.join(name).write('test')

    if is_borg_v2:
        subprocess.run(['borg', '-r', str(repo), 'rcreate', '--encryption=none'], check=True)
        subprocess.run(['borg', '-r', str(repo), 'create', 'a1', *wanted, 'other'], cwd=str(src), check=True)
    else:
        subprocess.run(['borg', 'init', '--encryption=none', str(repo)], check=True)
        subprocess.run(['borg', 'create', f'{repo}::a1', *wanted, 'other'], cwd=str(src), check=True)

    pattern_file = tmpdir.join('patterns')

    def include_file(name):
        data = FileData(FileType.FILE, 0, '', '', '', True, QDateTime())
        return _include_pattern(FileSystemItem((name,), data))

    pattern_file.write('P pf\n' + ''.join(include_file(name) + '\n' for name in wanted) + '- fm:*\n')

    archive = ['-r', str(repo), 'a1'] if is_borg_v2 else [f'{repo}::a1']
    subprocess.run(['borg', 'extract', *archive, '--patterns-from', str(pattern_file)], cwd=str(dest), check=True)

    assert sorted(item.basename for item in dest.listdir()) == sorted(wanted)
