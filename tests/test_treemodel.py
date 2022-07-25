from pathlib import PurePath

import pytest
from PyQt5.QtCore import QModelIndex

from vorta.views.partials.treemodel import FileSystemItem, FileTreeModel


class TreeModelImp(FileTreeModel):
    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 1

    def _make_filesystemitem(self, path, data):
        return super()._make_filesystemitem(path, data)

    def _merge_data(self, item, data):
        return super()._merge_data(item, data)


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

    def test_get(self):
        item = FileSystemItem(PurePath('test').parts, 0)
        child1 = FileSystemItem(PurePath('test/a').parts, 4)
        child2 = FileSystemItem(PurePath('test/b').parts, 3)
        child3 = FileSystemItem(PurePath('test/c').parts, 2)

        item.add(child1)
        item.add(child2)
        item.add(child3)

        # test get inexistent subpath
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
        assert (model.parent(model.indexPath(
            PurePath('test/subtest'))) == model.indexPath(PurePath('test')))

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
            (PurePath('c'), 9),
            (PurePath('c/a'), 10),
            (PurePath('c/a/b'), 11),
            (PurePath('c/a/b/c'), 12),
            (PurePath('c/a/b/a'), 13),
            (PurePath('c/a/b/a/b/c'), 14),
            (PurePath('c/a/b/b/c/a'), 15),
        ]

        model = TreeModelImp()
        model.addItems(items)

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
        assert model.parent(cababc).internalId() == cab.internalId()
        assert cabbca.internalPointer().data == 15
        assert model.parent(cabbca).internalId() == cab.internalId()
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
        assert caa.parent().internalId() == ca.internalId()

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
