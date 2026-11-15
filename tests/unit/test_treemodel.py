from pathlib import PurePath

import pytest
from PyQt6.QtCore import QModelIndex, Qt, qInstallMessageHandler

from vorta.views.partials.treemodel import FileSystemItem, FileTreeModel

SIMPLIFIED_TREE_ITEMS = [
    (PurePath('a'), 0),
    (PurePath('a/a'), 1),
    (PurePath('a/c'), 3),
    (PurePath('a/b/a'), 4),
    (PurePath('a/b/b'), 5),
    (PurePath('a/b'), 2),
    (PurePath('b'), 6),
    (PurePath('b/a'), 7),
    (PurePath('b/b'), 8),
    (PurePath('c'), 9),
    (PurePath('c/a'), 10),
    (PurePath('c/a/b'), 11),
    (PurePath('c/a/b/c'), 12),
    (PurePath('c/a/b/a'), 13),
    (PurePath('c/a/b/a/b/c'), 14),
    (PurePath('c/a/b/b/c/a'), 15),
]

# `b/c/d` collapses into a single row that is not at the same position as `d` inside `c`
COLLAPSED_CHAIN_ITEMS = [(PurePath(p), i) for i, p in enumerate(['a', 'a/x', 'a/w', 'b/c/d/e', 'b/c/d/f'])]

# the root holds only a chain, so the topmost merged item is a child of the root
SINGLE_CHAIN_ITEMS = [(PurePath('a/b/x'), 0), (PurePath('a/b/y'), 1)]

ITEM_LISTS = pytest.mark.parametrize(
    'items',
    [SIMPLIFIED_TREE_ITEMS, COLLAPSED_CHAIN_ITEMS, SINGLE_CHAIN_ITEMS],
    ids=['simplified_tree', 'collapsed_chain', 'single_chain'],
)
MODES = pytest.mark.parametrize('mode', list(FileTreeModel.DisplayMode), ids=lambda m: m.name)


class TreeModelImp(FileTreeModel):
    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 1

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.isValid() and role == Qt.ItemDataRole.DisplayRole:
            return index.internalPointer().subpath
        return None


def check_parents(model, parent=QModelIndex()):
    for row in range(model.rowCount(parent)):
        child = model.index(row, 0, parent)
        assert child.isValid() and child.row() == row
        assert model.parent(child) == parent
        check_parents(model, child)


def check_model(qtmodeltester, model, force_py):
    # The C++ tester only logs failures, which pytest-qt does not catch when capturing is off (`-s` in addopts).
    messages = []

    def handler(mode, context, message):
        if context.category == 'qt.modeltest':
            messages.append(message)

    previous = qInstallMessageHandler(handler)
    try:
        qtmodeltester.check(model, force_py=force_py)
    finally:
        qInstallMessageHandler(previous)
    assert not messages, '\n'.join(messages)


class TestFileSystemItem:
    def test_tuple(self):
        item = FileSystemItem(PurePath('test').parts, 0)

        assert item[0] == item.path
        assert item[1] == item.data

    def test_add(self):
        item = FileSystemItem(PurePath('test').parts, 0)

        assert len(item.children) == 0

        child = FileSystemItem(PurePath('test/hello').parts, 4)

        item.add(child)

        assert len(item.children) == 1
        assert item.children[0] == child
        assert child.subpath == 'hello'
        assert child._parent == item

        child = FileSystemItem(PurePath('test/hello').parts, 8)
        with pytest.raises(RuntimeError):
            # may not add a child with the same subpath
            item.add(child)

        # not implemented due to performance reasons:
        # child = FileSystemItem((), 8)
        # with pytest.raises(ValueError):
        #     item.add(child)  # may not add a child with an empty path

    def test_remove(self):
        item = FileSystemItem(PurePath('test').parts, 0)
        child1 = FileSystemItem(PurePath('test/a').parts, 4)
        child2 = FileSystemItem(PurePath('test/b').parts, 3)
        child3 = FileSystemItem(PurePath('test/c').parts, 2)

        item.add(child1)
        item.add(child2)
        item.add(child3)

        assert len(item.children) == 3

        # test remove subpath
        item.remove('b')
        assert len(item.children) == 2
        assert child2 not in item.children

        # test remove item
        item.remove(child3)
        assert len(item.children) == 1
        assert child3 not in item.children

        # test remove item not present
        child = FileSystemItem(PurePath('notpresent').parts, 2)
        with pytest.raises(ValueError):
            item.remove(child)
        child = FileSystemItem((), 2)
        with pytest.raises(ValueError):
            item.remove(child)

    def test_get(self):
        item = FileSystemItem(PurePath('test').parts, 0)
        child1 = FileSystemItem(PurePath('test/a').parts, 4)
        child2 = FileSystemItem(PurePath('test/b').parts, 3)
        child3 = FileSystemItem(PurePath('test/c').parts, 2)

        item.add(child1)
        item.add(child2)
        item.add(child3)

        # test get nonexistent subpath
        assert item.get('unknown') is None
        assert item.get('unknown', default='default') == 'default'

        # get subpath
        res = item.get('a')
        assert res is not None
        assert res[1] == child1

        res = item.get('b')
        assert res is not None
        assert res[1] == child2

        # get subpath of empty list
        assert child1.get('a') is None

    def test_get_subpath(self):
        item = FileSystemItem(('test',), 0)
        child1 = FileSystemItem(PurePath('test/a').parts, 4)
        child2 = FileSystemItem(PurePath('test/b').parts, 3)
        child3 = FileSystemItem(PurePath('test/c').parts, 2)

        item.add(child1)
        item.add(child2)
        item.add(child3)

        child11 = FileSystemItem(PurePath('test/a/aa').parts, 4)
        child1.add(child11)

        assert item.get_path(PurePath('a/aa').parts) is child11
        assert item.get_path(('b',)) is child2

        # test get empty path
        assert item.get_path(()) is item


class TestFileTreeModel:
    def test_basic_setup(self):
        model = TreeModelImp()

        assert model.rowCount() == 0

        # test FileTreeModel.addItem
        model.addItem((('test',), 0))
        assert model.rowCount() == 1

        item = model.getItem(('test',))
        assert item is not None
        assert item.subpath == 'test'
        assert len(item.children) == 0
        assert item.data == 0  # test id

        model.addItem((PurePath('/hello'), 1))
        model.addItem(FileSystemItem(PurePath('/hello/test').parts, 2))

        assert model.rowCount() == 2

        item = model.getItem(('/',))
        assert item is not None
        assert item.subpath == '/'
        assert len(item.children) == 1

        item = model.getItem(PurePath('/hello/test').parts)
        assert item is not None and item.data == 2

        # test adding Item to existing parent
        model.addItem((PurePath('test/subtest'), 3))
        assert model.rowCount() == 2
        item = model.getItem(PurePath('test/subtest').parts)
        assert item is not None and item.data == 3

        # test parent
        assert model.parent(model.indexPath(PurePath('test/subtest'))) == model.indexPath(PurePath('test'))

        # test index
        item1 = model.getItem(('test',))
        item2 = model.getItem(PurePath('test/subtest'))

        index1 = model.index(1, 0)
        assert index1.internalPointer() == item1
        assert index1 == model.indexPath(PurePath('test'))
        index2 = model.index(0, 0, index1)
        assert index2.internalPointer() == item2
        assert index2 == model.indexPath(PurePath('test/subtest'))

        # test rowCount
        assert model.rowCount() == 2
        assert model.rowCount(index1) == 1

        # test remove
        model.removeItem(('test',))
        assert model.rowCount() == 1
        assert item1 not in model.root.children

        model.removeItem(PurePath('/hello/test').parts)
        assert model.rowCount() == 1
        assert model.getItem(PurePath('/hello/test')) is None
        item3 = model.getItem(PurePath('/hello'))
        assert len(item3.children) == 0

    def test_empty_path(self):
        model = TreeModelImp()
        assert model.rowCount() == 0

        model.addItem(((), None))
        assert model.rowCount() == 0

        model.addItem((PurePath('.'), None))
        assert model.rowCount() == 0

    def test_root(self):
        model = TreeModelImp()
        assert model.getItem(PurePath()) == model.root

    def test_flat(self):
        items = [
            (PurePath('a'), 0),
            (PurePath('a/a'), 1),
            (PurePath('a/c'), 3),
            (PurePath('a/b/a'), 4),
            (PurePath('a/b/b'), 5),
            (PurePath('a/b'), 2),
            (PurePath('b'), 6),
            (PurePath('b/a'), 7),
            (PurePath('b/b'), 8),
        ]

        model = TreeModelImp()
        model.addItems(items)

        # test flat representation
        model.setMode(model.DisplayMode.FLAT)

        assert model.rowCount() == len(items)
        assert model.parent(model.index(4, 0)) == QModelIndex()
        assert model.rowCount(model.index(3, 0)) == 0

        item = model.getItem(PurePath('a/b/a'))
        assert item is not None and item.data == 4

        # test flat add
        model.addItem((PurePath('a/a/a'), 10))

        assert model.rowCount() == len(items) + 1
        item = model.getItem(PurePath('a/a/a'))
        assert item is not None and item.data == 10

        # test flat remove
        model.removeItem(PurePath('a/a/a'))

        assert model.rowCount() == len(items)
        assert item not in model._flattened

        # test flat indexPath
        index = model.indexPath(PurePath('a/b'))
        assert index.internalPointer().data == 2
        assert model._flattened[index.row()].data == 2
        assert index.parent() == QModelIndex()

        # test
        model.setMode(model.DisplayMode.TREE)

        assert model.rowCount() == 2

    def test_simplified_tree(self):
        model = TreeModelImp()
        model.addItems(SIMPLIFIED_TREE_ITEMS)

        # test tree representation
        model.setMode(model.DisplayMode.SIMPLIFIED_TREE)

        assert model.rowCount() == 3

        a = model.index(0, 0)
        assert model.rowCount(a) == 3
        ab = model.index(1, 0, a)
        assert model.rowCount(ab) == 2
        assert model.parent(ab) == a

        # test combined representation

        cab = model.index(2, 0)
        assert model.rowCount(cab) == 3
        assert cab.internalPointer().data == 11
        assert model.rowCount(cab) == 3
        assert model.parent(cab) == QModelIndex()
        cabc = model.index(2, 0, cab)
        cababc = model.index(0, 0, cab)
        cabbca = model.index(1, 0, cab)
        assert cababc.internalPointer().data == 14
        assert model.parent(cababc) == cab
        assert cabbca.internalPointer().data == 15
        assert model.parent(cabbca) == cab
        assert cabc.internalPointer().data == 12

        # test combined add
        model.addItem((PurePath('a/a/a'), 30))

        aaa = model.index(0, 0, a)
        assert aaa.internalPointer().data == 30
        assert model.rowCount(aaa) == 0

        model.addItem((PurePath('c/a/a'), 31))

        ca = model.index(2, 0)
        assert ca.internalPointer().data == 10
        assert ca.parent() == QModelIndex()
        assert model.rowCount(ca) == 2
        caa = model.index(0, 0, ca)
        assert caa.internalPointer().data == 31
        assert caa.parent() == ca

        # test combined remove
        model.removeItem(PurePath('a/a/a').parts)

        aa = model.index(0, 0, a)
        assert aa.internalPointer().data == 1
        assert model.rowCount(aa) == 0

        model.removeItem(PurePath('c/a/a'))

        cab = model.index(2, 0)
        assert cab.internalPointer().data == 11
        assert model.rowCount(cab) == 3

        # test combined indexPath
        index = model.indexPath(PurePath('a/b'))
        assert index.internalPointer().data == 2
        assert index.parent() == a

        index = model.indexPath(PurePath('c/a/b'))
        assert model.parent(index) == QModelIndex()
        assert index.internalPointer().data == 11
        assert model.rowCount(index) == 3

        index = model.indexPath(PurePath('c/a'))
        assert index == QModelIndex()

        # test mode change
        model.setMode(model.DisplayMode.TREE)

        assert model.rowCount() == 3

    @ITEM_LISTS
    @MODES
    def test_parent_matches_index(self, items, mode):
        model = TreeModelImp()
        model.addItems(items)
        model.setMode(mode)
        check_parents(model)

        model.addItem((PurePath('c/a/a'), 31))
        check_parents(model)

        model.removeItem(PurePath('c/a/a'))
        check_parents(model)

    def test_parent_row_of_collapsed_chain(self):
        model = TreeModelImp()
        model.addItems(COLLAPSED_CHAIN_ITEMS)
        model.setMode(model.DisplayMode.SIMPLIFIED_TREE)

        bcd = model.index(1, 0)
        assert model.index(0, 0, bcd).parent().row() == 1

    @ITEM_LISTS
    @MODES
    @pytest.mark.parametrize('force_py', [False, True])
    def test_model_tester(self, qtmodeltester, items, mode, force_py):
        model = TreeModelImp()
        model.addItems(items)
        model.setMode(mode)
        check_model(qtmodeltester, model, force_py)

    @pytest.mark.parametrize(
        'mode', [FileTreeModel.DisplayMode.TREE, FileTreeModel.DisplayMode.SIMPLIFIED_TREE], ids=lambda m: m.name
    )
    def test_index_out_of_range(self, mode):
        model = TreeModelImp()
        model.addItems(COLLAPSED_CHAIN_ITEMS)
        model.setMode(mode)

        top = model.index(0, 0)
        leaf = model.index(0, 0, top)
        for parent in [QModelIndex(), top, leaf]:
            assert not model.index(model.rowCount(parent), 0, parent).isValid()
            assert not model.index(-1, 0, parent).isValid()
            assert not model.index(0, 1, parent).isValid()

    @MODES
    def test_index_out_of_range_empty(self, mode):
        model = TreeModelImp()
        model.setMode(mode)
        assert not model.index(0, 0).isValid()
        assert not model.index(-1, 0).isValid()

    def test_index_out_of_range_flat(self):
        model = TreeModelImp()
        model.addItems(COLLAPSED_CHAIN_ITEMS)
        model.setMode(model.DisplayMode.FLAT)
        assert not model.index(model.rowCount(), 0).isValid()
        assert not model.index(-1, 0).isValid()
        assert not model.index(0, 1).isValid()
