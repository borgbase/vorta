"""
Implementation of a tree model for use with `QTreeView` based on (file) paths.

"""

import bisect
import enum
import os.path as osp
from functools import reduce
from pathlib import PurePath
from typing import Generic, List, Optional, Sequence, Tuple, TypeVar, Union, overload

from PyQt6.QtCore import (
    QAbstractItemModel,
    QModelIndex,
    QObject,
    QSortFilterProxyModel,
    Qt,
    pyqtSignal,
)

#: A representation of a path
Path = Tuple[str, ...]
PathLike = Union[Path, Sequence[str]]


def relative_path(p1: PathLike, p2: PathLike) -> Path:
    """Get p2 relative to p1."""
    if len(p2) <= len(p1):
        return ()

    return tuple(p2[len(p1) :])


def path_to_str(path: PathLike) -> str:
    """Return a string representation of a path."""
    if not path:
        return ''

    return osp.join(*path)


#: Type of FileSystemItem's data
T = TypeVar('T')
FileSystemItemLike = Union[Tuple[Union[PurePath, Path], Optional[T]], 'FileSystemItem']

#: Default return value
A = TypeVar('A')


class FileSystemItem(Generic[T]):
    """
    An item in the virtual file system.

    ..warning::

        Do not edit `children` manually. Always use `add` or `remove` or
        `sort`.

    Attributes
    ----------
    path : Path
        The path of this item.
    data : Any
        The data belonging to this item.
    children : List[FileSystemItem]
        The children of this item.
    _subpath : str
        The subpath of this item relative to its parent.
    _parent : FileSystemItem or None
        The parent of the item.
    """

    __slots__ = ['path', 'children', 'data', '_parent', 'subpath']

    def __init__(self, path: PathLike, data: T):
        """Init."""
        self.path: Path = tuple(path)
        self.data = data
        self.subpath: str = None
        self.children: List[FileSystemItem[T]] = []
        self._parent: Optional[FileSystemItem[T]] = None

    # @property
    # def subpath(self) -> str:
    #     """
    #     Get the name of the item which is the subpath relative to its parent.
    #     """
    #     return self.path[-1]

    # @property
    # def children(self):
    #     """Get an iterable view of the item's children."""
    #     return self.child_map.values()

    def add(self, child: 'FileSystemItem[T]', _subpath: str = None, _check: bool = True):
        """
        Add a child.

        The parameters starting with an underscore exist for performance
        reasons only. They should only be used if the operations that these
        parameters toggle were performed already.

        Parameters
        ----------
        child : FileSystemItem
            The child to add.
        _subpath : str, optional
            Precalculated subpath, default is None.
        _check : bool, optional
            Whether to check for children with the same subpath (using `get`).
        """
        if _subpath is not None:
            child.subpath = _subpath
        else:
            child.subpath = path_to_str(relative_path(self.path, child.path))

        i = bisect.bisect(self.children, child)

        # check for a child with the same subpath
        if _check and len(self.children) > i - 1 >= 0 and self.children[i - 1].subpath == child.subpath:
            raise RuntimeError("The subpath must be unique to a parent's children.")

        # add
        child._parent = self
        self.children.insert(i, child)

    def addChildren(self, children: List['FileSystemItem[T]']):
        """
        Add a list of children.

        Parameters
        ----------
        children : List[FileSystemItem]
            The children to add.
        """
        for child in children:
            self.add(child)

    @overload
    def remove(self, subpath: str) -> None:
        pass

    @overload
    def remove(self, index: int) -> None:
        pass

    @overload
    def remove(self, child: 'FileSystemItem[T]') -> None:
        pass

    def remove(self, child_subpath_index):
        """
        Remove the given children.

        The index or child to remove must be in the list
        else an error will be raised.

        Parameters
        ----------
        child_or_index : FileSystemItem or int
            The instance to remove or its index in `children`.

        Raises
        ------
        ValueError
            The given item is not a child of this one.
        IndexError
            The given index is not a valid one.
        """
        if isinstance(child_subpath_index, FileSystemItem):
            child = child_subpath_index
            if not child.subpath:
                raise ValueError("Child without subpath")

            i = bisect.bisect_left(self.children, child)
            if i < len(self.children) and self.children[i] == child:
                del self.children[i]
            else:
                raise ValueError("Child not found")

        elif isinstance(child_subpath_index, str):
            subpath = child_subpath_index
            i = bisect.bisect_left(self.children, subpath)
            if i < len(self.children) and self.children[i].subpath == subpath:
                del self.children[i]
            else:
                raise ValueError("Child not found")

        elif isinstance(child_subpath_index, int):
            i = child_subpath_index
            del self.children[i]

        else:
            raise TypeError(
                "First argument passed to `{}.remove` has invalid type {}".format(
                    type(self).__name__, type(child_subpath_index).__name__
                )
            )

    def __getitem__(self, index: int):
        """
        Get a an item.

        This allows accessing the attributes in the same manner for instances
        of this type and instances of `FileSystemItemLike`.
        """
        if index == 0:
            return self.path
        elif index == 1:
            return self.data
        else:
            raise IndexError("Index {} out of range(0, 2)".format(index))

    def get(self, subpath: str, default: Optional[A] = None) -> Union[Tuple[int, 'FileSystemItem[T]'], Optional[A]]:
        """
        Find direct child with given subpath.

        Parameters
        ----------
        subpath : str
            The items subpath relative to this.
        default : Any, optional
            The item to return if the child wasn't found, default None.

        Returns
        -------
        Tuple[int, FileSystemItem] or None
            The index and item if found else `default`.
        """
        i = bisect.bisect_left(self.children, subpath)
        if i < len(self.children):
            child = self.children[i]
            if child.subpath == subpath:
                return i, child
        return default

    def get_path(self, path: PathLike) -> Optional['FileSystemItem[T]']:
        """
        Get the item with the given subpath relative to this item.

        Parameters
        ----------
        path : Path
            The subpath.
        """

        def walk(fsi, pp):
            if fsi is None:
                return None
            res = fsi.get(pp)
            if not res:
                return None
            i, item = res
            return item

        fsi = reduce(walk, path, self)  # handles empty path -> returns self
        return fsi

    def __repr__(self):
        """Get a string representation."""
        return "FileSystemItem<'{}', '{}', {}, {}>".format(
            self.path,
            self.subpath,
            self.data,
            [c.subpath for c in self.children],
        )

    def __lt__(self, other):
        """Lower than for bisect sorting."""
        if isinstance(other, FileSystemItem):
            return self.subpath < other.subpath
        if isinstance(other, (list, tuple)):
            for s, o in zip(self.path, other):
                if s != o:
                    return s < o
            else:
                return len(self.path) < len(other)
        else:
            return self.subpath < other

    def __gt__(self, other):
        """Greater than for bisect sorting."""
        if isinstance(other, FileSystemItem):
            return self.subpath > other.subpath
        if isinstance(other, (list, tuple)):
            for s, o in zip(self.path, other):
                if s != o:
                    return s > o
            else:
                return len(self.path) > len(other)
        else:
            return self.subpath > other


class FileTreeModel(QAbstractItemModel, Generic[T]):
    """
    FileTreeModel managing a virtual file system with variable file data.

    Attributes
    ----------
    mode: DisplayMode
        The tree display mode of the model.

    Methods
    -------
    _make_filesystemitem(path, data, children)
        Construct a `FileSystemItem`.
    _merge_data(item, data)
        Add the given data to the item.
    _flat_filter
        Return whether an item is part of the flat model representation.
    flags
    columnCount
    headerData

    """

    class DisplayMode(enum.Enum):
        """
        The tree display modes available for the model.

        """

        #: normal file tree
        TREE = enum.auto()

        #: combine items in the tree having a single child with that child
        SIMPLIFIED_TREE = enum.auto()

        #: simple list of items
        FLAT = enum.auto()

    def __init__(self, mode: 'FileTreeModel.DisplayMode' = DisplayMode.TREE, parent=None):
        """Init."""
        super().__init__(parent)
        self.root: FileSystemItem[T] = FileSystemItem([], None)

        self.mode = mode
        #: flat representation of the tree
        self._flattened: List[FileSystemItem] = []

    def addItems(self, items: List[FileSystemItemLike[T]]):
        """
        Add file system items to the model.

        This method can be used for populating the model.
        Calls `addItem` for each item.

        Parameters
        ----------
        items : List[FileSystemItemLike]
            The items.
        """
        for item in items:
            self.addItem(item)

    def addItem(self, item: FileSystemItemLike[T]):
        """
        Add a file system item to the model.

        Parameters
        ----------
        item : FileSystemItemLike
            The item.
        """
        path = item[0]
        data = item[1]

        if isinstance(path, PurePath):
            path = path.parts

        if not path:
            return  # empty path (e.g. `.`) can't be added

        self.beginResetModel()

        def child(tup, subpath):
            fsi, i = tup
            i += 1
            return self._addChild(fsi, path[:i], subpath, None), i

        fsi, dummy = reduce(child, path[:-1], (self.root, 0))

        self._addChild(fsi, path, path[-1], data)

        self.endResetModel()

    def _addChild(
        self, item: FileSystemItem[T], path: PathLike, path_part: str, data: Optional[T]
    ) -> FileSystemItem[T]:
        """
        Add a child to an item.

        This is called by `addItem` in a reduce statement. It should
        add a new child with the given attributes to the given item.
        This implementation provides a reasonable default, most subclasses
        wont need to override this method. The implementation should make use
        of `_make_filesystemitem`, `_merge_data`, `_add_children`.

        Parameters
        ----------
        item : FileSystemItem
            The item to add a new child to.
        path : PathLike
            The path of the new child.
        path_part : str
            The subpath of the new child relative to `item`.
        data : Any or None
            The data of the new child.
        children : Any or None
            The initial children of the item.

        Returns
        -------
        FileSystemItem
            [description]
        """
        res = item.get(path_part)
        if res:
            i, child = res
            if data is not None:
                self._merge_data(child, data)
        else:
            child = self._make_filesystemitem(path, data)

            if self._flat_filter(child):
                i = bisect.bisect(self._flattened, child.path)
                self._flattened.insert(i, child)

            item.add(child, _subpath=path_part, _check=False)

            # update parent data
            self._process_child(child)

        return child

    def _make_filesystemitem(self, path: PathLike, data: Optional[T]) -> FileSystemItem[T]:
        """
        Construct a `FileSystemItem`.

        The attributes are the attributes of a `FileSystemItemLike`.
        This implementation already provides reasonable default that
        subclasses can be used.

        ..warning:: Do always call `_addChild` to add a child to an item.

        Parameters
        ----------
        path : PathLike
            The path of the item.
        data : Any or None
            The data.
        children : Any or None
            The initial children.

        Returns
        -------
        FileSystemItem
            The FileSystemItem for the internal tree structure.
        """
        return FileSystemItem(path, data)

    def _process_child(self, child: FileSystemItem[T]):
        """
        Process a new child.

        This can make some changes to the child's data like
        setting a default value if the child's data is None.
        This can also update the data of the parent.

        Parameters
        ----------
        child : FileSystemItem
            The child that was added.
        """
        pass  # Does nothing

    def _merge_data(self, item: FileSystemItem[T], data: Optional[T]):
        """
        Add the given data to the item.

        This method is called by `_addChild` which in turn is called by
        `addItem`. It gets an item in the virtual file system that was
        added again with the given data. The data may be None.

        Parameters
        ----------
        item : FileSystemItem
            The item to merge the data in.
        data : Any or None
            The data to add.
        """
        if not item.data:
            item.data = data

    def removeItem(self, path: Union[PurePath, PathLike]) -> None:
        """
        Remove an item from the model.

        Parameters
        ----------
        path : PathLike or PurePath
            The path of the item to remove.
        """
        if isinstance(path, PurePath):
            path = path.parts

        if not path:
            return

        self.beginResetModel()

        parent = self.getItem(path[:-1])

        if not parent:
            return

        res = parent.get(path[-1])

        if not res:
            return

        i, item = res

        # remove item and its children in flat representation
        items_to_remove: List[FileSystemItem] = [item]
        while items_to_remove:
            to_remove = items_to_remove.pop()

            fi = bisect.bisect_left(self._flattened, to_remove.path)
            if fi < len(self._flattened) and self._flattened[fi] is to_remove:
                del self._flattened[fi]

            items_to_remove.extend(to_remove.children)

        # remove item from tree representation
        parent.remove(i)

        self.endResetModel()

    def setMode(self, value: 'DisplayMode'):
        """
        Set the display mode of the tree model.

        In TREE mode (default) the tree will be displayed as is.
        In SIMPLIFIED_TREE items will simplify the tree by combining
        items with their single child if they posess only one.
        In FLAT mode items will be displayed as a simple list. The items
        shown can be filtered by `_flat_filter`.

        Parameters
        ----------
        value : bool
            The new value for the attribute.

        See also
        --------
        getMode: Get the current mode.
        _flat_filter
        """
        if value == self.mode:
            return  # nothing to do

        self.beginResetModel()
        self.mode = value
        self.endResetModel()

    def getMode(self) -> bool:
        """
        Get the display mode set.

        Returns
        -------
        DisplayMode
            The current value.

        See also
        --------
        setMode : Set the mode.
        """
        return self.mode

    def _flat_filter(self, item: FileSystemItem[T]) -> bool:
        """
        Return whether an item is part of the flat model representation.
        """
        return True

    def _simplify_filter(self, item: FileSystemItem[T]) -> bool:
        """
        Return whether an item may be merged in simplified mode.
        """
        return True

    def getItem(self, path: Union[PurePath, PathLike]) -> Optional[FileSystemItem[T]]:
        """
        Get the item with the given path.

        Parameters
        ----------
        path : PathLike or PurePath
            The path of the item.

        Returns
        -------
        Optional[FileSystemItem]
            [description]
        """
        if isinstance(path, PurePath):
            path = path.parts

        return self.root.get_path(path)  # handels empty path

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        """
        Get the data for the given role and index.

        The indexes internal pointer references the corresponding
        `FileSystemItem`.

        Parameters
        ----------
        index : QModelIndex
            The index of the item.
        role : int, optional
            The data role, by default Qt.ItemDataRole.DisplayRole

        Returns
        -------
        Any
            The data, return None if no data is available for the role.
        """
        return super().data(index, role)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """
        Returns the number of rows under the given parent.

        When the parent is valid it means that rowCount is returning
        the number of children of parent.

        Parameters
        ----------
        parent : QModelIndex, optional
            The index of the parent item, by default QModelIndex()

        Returns
        -------
        int
            The number of children.
        """
        if parent.column() > 0:
            return 0  # Only the first column has children

        # flat mode
        if self.mode == self.DisplayMode.FLAT:
            if not parent.isValid():
                return len(self._flattened)
            return 0

        # tree mode
        if not parent.isValid():
            parent_item: FileSystemItem = self.root
        else:
            parent_item = parent.internalPointer()

        return len(parent_item.children)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """
        Returns the number of columns for the children of the given parent.

        This corresponds to the number of data (column) entries shown
        for each item in the tree view.

        Parameters
        ----------
        parent : QModelIndex, optional
            The index of the parent, by default QModelIndex()

        Returns
        -------
        int
            The number of rows.
        """
        raise NotImplementedError("Method `columnCount` of FileTreeModel" + " must be implemented by subclasses.")

    def indexPath(self, path: Union[PurePath, PathLike]) -> QModelIndex:
        """
        Construct a `QModelIndex` for the given path.

        If `combine` is enabled, the closest indexed parent path is returned.

        Parameters
        ----------
        path : PurePath or PathLike
            The path to the item the index should point to.

        Returns
        -------
        QModelIndex
            The requested index.
        """
        if isinstance(path, PurePath):
            path = path.parts

        if not path:
            return QModelIndex()  # empty path won't ever be in the model

        # flat mode
        if self.mode == self.DisplayMode.FLAT:
            i = bisect.bisect_left(self._flattened, path)
            if i < len(self._flattened) and self._flattened[i].path == path:
                return self.index(i, 0)
            return QModelIndex()

        # tree mode
        simplified = self.mode == self.DisplayMode.SIMPLIFIED_TREE

        def step(tup, subpath):
            index, i, item = tup

            if not item:
                return index, None

            r, child = item.get(subpath)

            if not child:
                return QModelIndex(), None

            if i <= -1:
                i = r

            if simplified and len(child.children) == 1 and self._simplify_filter(child):
                return index, i, child

            index = self.index(i if simplified else r, 0, index)

            return index, -1, child

        index, i, item = reduce(step, path, (QModelIndex(), -1, self.root))

        return index

    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
        """
        Construct a `QModelIndex`.

        Returns the index of the item in the model specified by
        the given row, column and parent index.

        Parameters
        ----------
        row : int
        column : int
        parent : QModelIndex, optional

        Returns
        -------
        QModelIndex
            The requested index.
        """
        # different behavior in flat and treemode
        if self.mode == self.DisplayMode.FLAT:
            if 0 <= row < len(self._flattened) and 0 <= column < self.columnCount(parent):
                return self.createIndex(row, column, self._flattened[row])

            return QModelIndex()

        # valid index?
        if not parent.isValid():
            parent_item: FileSystemItem[T] = self.root
        else:
            parent_item = parent.internalPointer()

        item = list(parent_item.children)[row]

        if self.mode == self.DisplayMode.SIMPLIFIED_TREE:
            # combine items with a single child with that child
            while len(item.children) == 1 and self._simplify_filter(item):
                item = item.children[0]

        if 0 <= row < len(parent_item.children) and 0 <= column < self.columnCount(parent):
            return self.createIndex(row, column, item)

        return QModelIndex()

    @overload
    def parent(self, child: QModelIndex) -> QModelIndex:
        pass

    @overload
    def parent(self) -> QObject:
        pass

    def parent(self, child=None):
        """
        Returns the parent of the model item with the given index.

        If the item has no parent, an invalid QModelIndex is returned.
        A common convention used in models that expose tree data structures
        is that only items in the first column have children.
        For that case, when reimplementing this function in a subclass
        the column of the returned QModelIndex would be 0.

        Parameters
        ----------
        child : QModelIndex
            The index of the child item.

        Returns
        -------
        QModelIndex
            The index of the parent item.
        """
        # overloaded variant to retrieve parent of model
        if child is None:
            return super().parent()

        # variant to retrieve parent for data item
        if not child.isValid():
            return QModelIndex()

        # different behavior in tree and flat mode
        if self.mode == self.DisplayMode.FLAT:
            return QModelIndex()  # in flat mode their are no parents

        child_item: FileSystemItem[T] = child.internalPointer()
        parent_item = child_item._parent

        if self.mode == self.DisplayMode.SIMPLIFIED_TREE:
            # combine items with a single child with the child
            while (
                parent_item is not self.root  # do not call filter with root
                and len(parent_item.children) == 1
                and self._simplify_filter(parent_item)
            ):
                parent_item = parent_item._parent

        if parent_item is self.root:
            # Never return root item since it shouldn't be displayed
            return QModelIndex()

        row, item = parent_item._parent.get(parent_item.subpath)
        return self.createIndex(row, 0, parent_item)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """
        Returns the item flags for the given index.

        The base class implementation returns a combination of flags
        that enables the item (ItemIsEnabled) and
        allows it to be selected (ItemIsSelectable).

        Parameters
        ----------
        index : QModelIndex
            The index.

        Returns
        -------
        Qt.ItemFlags
            The flags.
        """
        return super().flags(index)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        """
        Get the data for the given role and section in the given header.

        The header is identified by its orientation.
        For horizontal headers, the section number corresponds to
        the column number. Similarly, for vertical headers,
        the section number corresponds to the row number.

        Parameters
        ----------
        section : int
            The row or column number.
        orientation : Qt.Orientation
            The orientation of the header.
        role : int, optional
            The data role, by default Qt.ItemDataRole.DisplayRole

        Returns
        -------
        Any
            The data for the specified header section.
        """
        return super().headerData(section, orientation, role)


class FileTreeSortProxyModel(QSortFilterProxyModel):
    """
    Sort a FileTreeModel.
    """

    sorted = pyqtSignal(int, Qt.SortOrder)

    def __init__(self, parent=None) -> None:
        """Init."""
        super().__init__(parent)
        self.folders_on_top = False

    @overload
    def keepFoldersOnTop(self) -> bool:
        ...

    @overload
    def keepFoldersOnTop(self, value: bool) -> bool:
        ...

    def keepFoldersOnTop(self, value=None) -> bool:
        """
        Set or get whether folders are kept on top when sorting.

        Parameters
        ----------
        value : bool, optional
            The new value, by default None

        Returns
        -------
        bool
            The value of the attribute.
        """
        if value is not None and value != self.folders_on_top:
            self.folders_on_top = value
            # resort
            self.setDynamicSortFilter(False)
            self.sort(self.sortColumn(), self.sortOrder())
            self.setDynamicSortFilter(True)

        return self.folders_on_top

    def extract_path(self, index: QModelIndex):
        """Get the path to compare for a given index."""
        item: FileSystemItem = index.internalPointer()
        model: FileTreeModel = self.sourceModel()

        # name
        if model.mode == FileTreeModel.DisplayMode.FLAT:
            return path_to_str(item.path)

        if model.mode == FileTreeModel.DisplayMode.SIMPLIFIED_TREE:
            parent = index.parent()
            if parent == QModelIndex():
                path = relative_path(model.root.path, item.path)
            else:
                path = relative_path(parent.internalPointer().path, item.path)

            return path[0] if path else ''

        # standard tree mode
        return item.subpath

    def choose_data(self, index: QModelIndex):
        """Choose the data of index used for comparison."""
        raise NotImplementedError(
            "Method `choose_data` of " + "FileTreeSortProxyModel" + " must be implemented by subclasses."
        )

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        """
        Return whether the item of `left` is lower than the one of `right`.
        Parameters
        ----------
        left : QModelIndex
            The index left of the `<`.
        right : QModelIndex
            The index right of the `<`.
        Returns
        -------
        bool
            Whether left is lower than right.
        """
        if self.folders_on_top:
            item1 = left.internalPointer()
            item2 = right.internalPointer()
            ch1 = bool(len(item1.children))
            ch2 = bool(len(item2.children))

            if ch1 ^ ch2:
                if self.sortOrder() == Qt.SortOrder.AscendingOrder:
                    return ch1
                return ch2

        data1 = self.choose_data(left)
        data2 = self.choose_data(right)
        return data1 < data2
