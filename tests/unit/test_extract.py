import fnmatch
import re

import pytest
from PyQt6.QtCore import QDateTime, QModelIndex, Qt

import vorta.borg
from vorta.borg.extract import BorgExtractJob, _include_pattern
from vorta.store.models import ArchiveModel, BackupProfileModel
from vorta.views.dialogs.archive.extract import (
    ExtractDialog,
    ExtractSortProxyModel,
    ExtractTree,
    FileData,
    FileType,
    parse_json_lines,
)
from vorta.views.partials.treemodel import FileSystemItem, FileTreeModel


def prepare_borg(mocker, borg_json_output):
    stdout, stderr = borg_json_output("list_archive")
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, "Popen", return_value=popen_result)


default = {
    "mode": "drwxrwxr-x",
    "user": "theuser",
    "group": "theuser",
    "uid": 1000,
    "gid": 1000,
    "path": "",
    "healthy": True,
    "source": "",
    "linktarget": "",
    "flags": None,
    "mtime": "2022-05-13T14:33:57.305797",
    "isomtime": "2022-05-13T14:33:57.305797",
    "size": 0,
}


def updated(path, values):
    d = default.copy()
    d.update(values)
    d["path"] = path
    return d


def test_parser():
    """Test creating a tree with correct data from json lines."""

    lines = [
        updated("a", {}),
        updated("a/b", {"mode": "-rwxrwxr-x"}),
        updated("a/b/c", {}),
        updated("a/b/d", {}),
        updated("a/a", {}),
        updated("a/a/a", {}),
        updated("a/a/b", {}),
        updated("a/a/c", {"healthy": False}),
        updated("a/a/d", {}),
        updated("a/a/e", {}),
    ]

    model = ExtractTree()
    parse_json_lines(lines, model)

    index = model.indexPath(("a", "b"))
    assert index != QModelIndex()
    assert index.internalPointer().data.file_type == FileType.FILE

    item = model.getItem(("a", "a", "c"))
    assert item
    assert item.data.health is False


def select(model, index):
    model.setData(index, Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)


def deselect(model, index):
    model.setData(index, Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)


def test_lazy_selection_overlapping_paths():
    model = ExtractTree()
    parse_json_lines([updated(path, {}) for path in ("a", "a/b", "a/b/c", "a/b/d", "a/e")], model)

    def state(*path):
        return model.data(model.indexPath(path), Qt.ItemDataRole.CheckStateRole)

    select(model, model.indexPath(("a",)))
    deselect(model, model.indexPath(("a", "b")))
    select(model, model.indexPath(("a", "b", "c")))
    assert state("a") == Qt.CheckState.PartiallyChecked
    assert state("a", "b") == Qt.CheckState.PartiallyChecked
    assert state("a", "b", "c") == Qt.CheckState.Checked
    assert state("a", "b", "d") == Qt.CheckState.Unchecked
    assert state("a", "e") == Qt.CheckState.Checked

    select(model, model.indexPath(("a", "b")))
    assert state("a") == Qt.CheckState.Checked
    assert state("a", "b") == Qt.CheckState.Checked
    assert state("a", "b", "c") == Qt.CheckState.Checked
    assert state("a", "b", "d") == Qt.CheckState.Checked
    assert model.explicit_selects == [("a",)]
    assert model.explicit_deselects == []

    deselect(model, model.indexPath(("a",)))
    assert state("a") == Qt.CheckState.Unchecked
    assert state("a", "b", "c") == Qt.CheckState.Unchecked
    assert model.explicit_selects == []
    assert model.explicit_deselects == []

    select(model, model.indexPath(("a", "b", "c")))
    assert state("a") == Qt.CheckState.PartiallyChecked
    assert state("a", "b") == Qt.CheckState.PartiallyChecked
    assert state("a", "b", "c") == Qt.CheckState.Checked
    assert state("a", "b", "d") == Qt.CheckState.Unchecked

    select(model, model.indexPath(("a",)))
    assert state("a") == Qt.CheckState.Checked
    assert state("a", "b", "d") == Qt.CheckState.Checked
    assert model.explicit_selects == [("a",)]


def test_selection():
    """Test selecting items for extraction."""
    lines = [
        updated("a", {}),
        updated("a/b", {}),
        updated("a/b/c", {}),
        updated("a/b/d", {}),
        updated("a/a", {}),
        updated("a/a/a", {}),
        updated("a/a/b", {}),
        updated("a/a/c", {}),
        updated("a/a/d", {}),
        updated("a/a/e", {}),
        updated("c", {}),
    ]
    model = ExtractTree()
    parse_json_lines(lines, model)

    def state(*path):
        return model.data(model.indexPath(path), Qt.ItemDataRole.CheckStateRole)

    ic = model.indexPath(("c",))
    select(model, ic)
    assert state("c") == Qt.CheckState.Checked
    deselect(model, ic)
    assert state("c") == Qt.CheckState.Unchecked

    ia = model.indexPath(("a",))
    iab = model.indexPath(("a", "b"))
    iaa = model.indexPath(("a", "a"))
    iaac = model.indexPath(("a", "a", "c"))

    select(model, ia)
    for path in (("a",), ("a", "a"), ("a", "a", "b"), ("a", "b"), ("a", "b", "c")):
        assert state(*path) == Qt.CheckState.Checked

    deselect(model, iab)
    assert state("a") == Qt.CheckState.PartiallyChecked
    assert state("a", "a") == Qt.CheckState.Checked
    assert state("a", "b") == Qt.CheckState.Unchecked
    assert state("a", "b", "c") == Qt.CheckState.Unchecked

    deselect(model, ia)
    assert state("a") == Qt.CheckState.Unchecked
    assert state("a", "a") == Qt.CheckState.Unchecked
    assert state("a", "b") == Qt.CheckState.Unchecked

    select(model, ia)
    deselect(model, iab)
    deselect(model, iaac)
    select(model, iab)
    select(model, iaac)
    assert state("a") == Qt.CheckState.Checked
    assert state("a", "a") == Qt.CheckState.Checked
    assert state("a", "b") == Qt.CheckState.Checked

    deselect(model, iaa)
    deselect(model, iab)
    assert state("a") == Qt.CheckState.PartiallyChecked
    assert state("a", "a") == Qt.CheckState.Unchecked
    assert state("a", "b") == Qt.CheckState.Unchecked

    select(model, iaac)
    assert state("a") == Qt.CheckState.PartiallyChecked
    assert state("a", "a") == Qt.CheckState.PartiallyChecked
    assert state("a", "b") == Qt.CheckState.Unchecked

    select(model, iaa)
    assert state("a", "a") == Qt.CheckState.Checked
    assert state("a") == Qt.CheckState.PartiallyChecked

    select(model, iab)
    assert state("a") == Qt.CheckState.Checked


@pytest.mark.parametrize(
    "selection, expected_mode, expected_bCollapseAllEnabled",
    [(0, FileTreeModel.DisplayMode.TREE, True), (1, FileTreeModel.DisplayMode.SIMPLIFIED_TREE, True)],
)
def test_change_display_mode(selection: int, expected_mode, expected_bCollapseAllEnabled):
    dialog = ExtractDialog(ArchiveModel(), ExtractTree())
    dialog.change_display_mode(selection)

    assert dialog.model.mode == expected_mode
    assert dialog.bCollapseAll.isEnabled() == expected_bCollapseAllEnabled


def borg_fnmatch(pattern, path):
    """Mimic borg's FnmatchPattern matching of an item and everything below it."""
    return re.match(fnmatch.translate(pattern + '/*'), path + '/') is not None


@pytest.mark.parametrize(
    "path, expected",
    [
        ("home/user/file", "+ home/user/file"),
        ("home/a b/file", "+ home/a b/file"),
        ("home/x\nPRIMARY y", "+ fm:home/x?PRIMARY y"),
        ("home/x\r\ny", "+ fm:home/x??y"),
        ("home/trailing ", "+ fm:home/trailing?"),
        ("home/tab\t", "+ fm:home/tab?"),
        (" lead", "+ fm:?lead"),
        ("home/[a]*?\nb", "+ fm:home/[[]a][*][?]?b"),
    ],
)
def test_include_pattern(path, expected):
    assert _include_pattern(path) == expected

    line = _include_pattern(path)
    assert len(line.splitlines()) == 1
    assert line == line.strip()
    if line.startswith('+ fm:'):
        pattern = line[len('+ fm:') :]
        assert borg_fnmatch(pattern, path)
        assert borg_fnmatch(pattern, path + '/child')


def test_include_pattern_escapes_metachars():
    pattern = _include_pattern("d/[a]*?\n")[len('+ fm:') :]
    assert borg_fnmatch(pattern, "d/[a]*?\n")
    assert not borg_fnmatch(pattern, "d/a*?\n")
    assert not borg_fnmatch(pattern, "d/[a]xx\n")


def test_extract_prepare_selected_directory(qapp):
    lines = [
        updated("a", {}),
        updated("a/x\nPRIMARY y", {"mode": "-rw-r--r--"}),
        updated("a/trailing ", {"mode": "-rw-r--r--"}),
        updated("a/plain", {"mode": "-rw-r--r--"}),
    ]
    model = ExtractTree()
    parse_json_lines(lines, model)
    select(model, model.indexPath(("a",)))

    profile = BackupProfileModel.get()
    ret = BorgExtractJob.prepare(profile, 'archive', model, '/tmp')
    assert ret['ok']

    with open(ret['cleanup_files'][0].name) as f:
        content = f.read().splitlines()

    assert content == ["P pp", "+ a", "- fm:*"]


def test_extract_prepare_partial_directory(qapp):
    lines = [
        updated("a", {}),
        updated("a/x\nPRIMARY y", {"mode": "-rw-r--r--"}),
        updated("a/trailing ", {"mode": "-rw-r--r--"}),
        updated("a/plain", {"mode": "-rw-r--r--"}),
        updated("a/b", {}),
        updated("a/b/keep", {"mode": "-rw-r--r--"}),
        updated("a/b/skip", {"mode": "-rw-r--r--"}),
    ]
    model = ExtractTree()
    parse_json_lines(lines, model)
    select(model, model.indexPath(("a",)))
    deselect(model, model.indexPath(("a", "b", "skip")))

    profile = BackupProfileModel.get()
    ret = BorgExtractJob.prepare(profile, 'archive', model, '/tmp')
    assert ret['ok']

    with open(ret['cleanup_files'][0].name) as f:
        content = f.read().splitlines()

    assert content[0] == "P pp"
    assert content[-1] == "- fm:*"
    assert set(content[1:-1]) == {
        "+ fm:a/x?PRIMARY y",
        "+ fm:a/trailing?",
        "+ a/plain",
        "+ a/b/keep",
    }


def test_parser_borg2_format():
    """Test parsing json lines formatted by Borg 2.0 or with health strings."""
    lines = [
        {
            "path": "healthy_file.txt",
            "size": 1024,
            "mode": "-rw-r--r--",
            "user": "root",
            "group": "root",
            "health": "healthy",
            "mtime": "2024-01-01T12:00:00",
        },
        {
            "path": "broken_file.txt",
            "size": 512,
            "mode": "-rw-r--r--",
            "user": "root",
            "group": "root",
            "health": "broken",
            "mtime": "2024-01-01T12:00:00",
        },
        {
            "path": "omitted_health.txt",
            "size": 256,
            "mode": "-rw-r--r--",
            "mtime": "2024-01-01T12:00:00",
        },
    ]

    model = ExtractTree()
    parse_json_lines(lines, model)

    healthy_item = model.getItem(("healthy_file.txt",))
    assert healthy_item is not None
    assert healthy_item.data.health is True
    assert healthy_item.data.size == 1024

    broken_item = model.getItem(("broken_file.txt",))
    assert broken_item is not None
    assert broken_item.data.health is False

    omitted_item = model.getItem(("omitted_health.txt",))
    assert omitted_item is not None
    assert omitted_item.data.health is True
    assert omitted_item.data.user == ""
    assert omitted_item.data.group == ""


def test_extract_sort_proxy_empty_data():
    """Test sorting proxy handles empty/None items without TypeError across columns."""
    proxy = ExtractSortProxyModel()
    model = ExtractTree()
    proxy.setSourceModel(model)

    # Invalid QModelIndex
    invalid_index = QModelIndex()
    assert proxy.choose_data(invalid_index) == ""

    # Test columns with None internalPointer
    idx0 = model.createIndex(0, 0, None)
    idx1 = model.createIndex(0, 1, None)
    idx2 = model.createIndex(0, 2, None)
    idx3 = model.createIndex(0, 3, None)

    assert proxy.choose_data(idx0) == ""
    empty_dt = proxy.choose_data(idx1)
    assert isinstance(empty_dt, QDateTime)
    assert (empty_dt < QDateTime.currentDateTime()) is True
    assert proxy.choose_data(idx2) == -1
    assert (-1 < 1024) is True
    assert proxy.choose_data(idx3) is False
    assert (False < True) is True

    # Test columns where item.data is None
    fsi = FileSystemItem(["folder"], None)
    fsi_idx1 = model.createIndex(0, 1, fsi)
    fsi_idx2 = model.createIndex(0, 2, fsi)
    fsi_idx3 = model.createIndex(0, 3, fsi)

    assert isinstance(proxy.choose_data(fsi_idx1), QDateTime)
    assert proxy.choose_data(fsi_idx2) == -1
    assert proxy.choose_data(fsi_idx3) is False


def test_simplified_proxy_parent():
    model = ExtractTree()
    paths = ['a', 'a/x', 'a/w', 'b', 'b/c', 'b/c/d', 'b/c/d/e', 'b/c/d/f']
    parse_json_lines([updated(p, {}) for p in paths], model)

    model.setMode(model.DisplayMode.SIMPLIFIED_TREE)
    proxy = ExtractSortProxyModel()
    proxy.setSourceModel(model)
    proxy.sort(0)

    bcd = model.index(1, 0)
    e = model.index(0, 0, bcd)
    assert e.parent() == bcd

    proxy_e = proxy.mapFromSource(e)
    assert proxy_e.parent() == proxy.mapFromSource(bcd)
    assert proxy_e.parent().data() == 'b/c/d'
    assert proxy.mapToSource(proxy_e) == e
