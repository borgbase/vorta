import pytest
import vorta.borg
from PyQt6.QtCore import QModelIndex, Qt
from vorta.store.models import ArchiveModel
from vorta.views.extract_dialog import (
    ExtractDialog,
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
    "isomtime": "2023-08-17T00:00:00.000000",
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

    # Test select
    ic = model.index(1, 0, QModelIndex())
    c: FileSystemItem[FileData] = ic.internalPointer()

    select(model, ic)
    assert c.data.checkstate == Qt.CheckState(2)
    assert c.data.checked_children == 0

    # Test deselect
    deselect(model, ic)
    assert c.data.checkstate == Qt.CheckState(0)
    assert c.data.checked_children == 0

    # Test select parent as well as children
    ia = model.index(0, 0, QModelIndex())
    a: FileSystemItem[FileData] = ia.internalPointer()
    aa = model.getItem(("a", "a"))
    aab = model.getItem(("a", "a", "b"))
    ab = model.getItem(("a", "b"))
    abc = model.getItem(("a", "b", "c"))

    select(model, ia)
    assert a.data.checkstate
    assert a.data.checked_children == 2
    assert a.data.checked_children == 2
    assert aab.data.checkstate
    assert ab.data.checkstate
    assert aa.data.checkstate
    assert aa.data.checked_children == 5

    # Test deselect item as well as children with selected parent
    iab = model.indexPath(("a", "b"))
    deselect(model, iab)

    assert a.data.checkstate == Qt.CheckState(1)
    assert aa.data.checkstate == Qt.CheckState(2)
    assert ab.data.checkstate == Qt.CheckState(0)
    assert abc.data.checkstate == Qt.CheckState(0)
    assert a.data.checked_children == 1
    assert ab.data.checked_children == 0

    # Test deselect item and children
    deselect(model, ia)

    assert a.data.checkstate == Qt.CheckState(0)
    assert aa.data.checkstate == Qt.CheckState(0)
    assert ab.data.checkstate == Qt.CheckState(0)
    assert a.data.checked_children == 0
    assert aa.data.checked_children == 0

    # Test select child with partially selected parent
    iaac = model.indexPath(("a", "a", "c"))

    select(model, ia)
    deselect(model, iab)
    deselect(model, iaac)
    select(model, iab)
    select(model, iaac)

    assert a.data.checkstate == Qt.CheckState(1)
    assert aa.data.checkstate == Qt.CheckState(1)
    assert ab.data.checkstate == Qt.CheckState(2)

    assert a.data.checked_children == 2
    assert ab.data.checked_children == 2
    assert aa.data.checked_children == 5

    # Test deselect all children with selected parent
    iaa = model.indexPath(("a", "a"))
    deselect(model, iaa)
    deselect(model, iab)

    assert a.data.checkstate == Qt.CheckState(0)
    assert a.data.checked_children == 0

    # Test select child with deselected parent
    select(model, iaac)

    assert a.data.checkstate == Qt.CheckState(1)
    assert ab.data.checkstate == Qt.CheckState(0)
    assert aa.data.checkstate == Qt.CheckState(1)
    assert a.data.checked_children == 1
    assert ab.data.checked_children == 0
    assert aa.data.checked_children == 1

    select(model, iaa)
    assert a.data.checkstate == Qt.CheckState(1)

    select(model, iab)
    assert a.data.checkstate == Qt.CheckState(1)


@pytest.mark.parametrize(
    "selection, expected_mode, expected_bCollapseAllEnabled",
    [(0, FileTreeModel.DisplayMode.TREE, True), (1, FileTreeModel.DisplayMode.SIMPLIFIED_TREE, True)],
)
def test_change_display_mode(selection: int, expected_mode, expected_bCollapseAllEnabled):
    dialog = ExtractDialog(ArchiveModel(), ExtractTree())
    dialog.change_display_mode(selection)

    assert dialog.model.mode == expected_mode
    assert dialog.bCollapseAll.isEnabled() == expected_bCollapseAllEnabled


@pytest.mark.parametrize(
    'search_string,expected_search_results',
    [
        # Normal "in" search
        ('txt', ['hello.txt', 'file1.txt', 'file.txt']),
        # Ignore Case
        ('HELLO.txt -i', ['hello.txt']),
        ('HELLO.txt', []),
        # Size Match
        ('--size >=15MB', []),
        ('--size >9MB,<11MB', ['abigfile.pdf']),
        ('--size >1KB,<4KB --exclude-parents', ['hello.txt']),
        # Path Match Type
        ('home/kali/vorta/source1/hello.txt --path', ['hello.txt']),
        ('home/kali/vorta/source1/file*.txt --path -m fm', ['file1.txt', 'file.txt']),
        # Regex Match Type
        ("file[^/]*\\.txt|\\.pdf -m re", ['file1.txt', 'file.txt', 'abigfile.pdf']),
        # Exact Match Type
        ('hello', ['hello.txt']),
        ('hello -m ex', []),
        # Extract Specific Filters #
        # Date Filter
        ('--last-modified >2025-01-01', ['file.txt']),
        ('--last-modified <2025-01-01 --exclude-parents', ['hello.txt', 'file1.txt', 'abigfile.pdf']),
        # Health match
        ('--unhealthy', ['abigfile.pdf']),
        ('--healthy', ['hello.txt', 'file1.txt', 'file.txt', 'abigfile.pdf']),
    ],
)
def test_archive_extract_filters(
    qtbot, mocker, borg_json_output, search_visible_items_in_tree, archive_env, search_string, expected_search_results
):
    """
    Tests the supported search filters for the extract window.
    """

    vorta.utils.borg_compat.version = '1.2.4'

    _, tab = archive_env
    tab.archiveTable.selectRow(0)

    stdout, stderr = borg_json_output('extract_archives_search')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    # click on extract button
    qtbot.mouseClick(tab.bExtract, Qt.MouseButton.LeftButton)

    # Wait for window to open
    qtbot.waitUntil(lambda: hasattr(tab, '_window'), **pytest._wait_defaults)
    qtbot.waitUntil(lambda: tab._window.treeView.model().rowCount(QModelIndex()) > 0, **pytest._wait_defaults)

    tab._window.searchWidget.setText(search_string)
    qtbot.mouseClick(tab._window.bSearch, Qt.MouseButton.LeftButton)

    qtbot.waitUntil(
        lambda: (tab._window.treeView.model().rowCount(QModelIndex()) > 0) or (len(expected_search_results) == 0),
        **pytest._wait_defaults,
    )

    proxy_model = tab._window.treeView.model()

    filtered_items = search_visible_items_in_tree(proxy_model, QModelIndex())

    # sort both lists to make sure the order is not important
    filtered_items.sort()
    expected_search_results.sort()

    assert filtered_items == expected_search_results
    vorta.utils.borg_compat.version = '1.1.0'
