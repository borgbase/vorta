from pathlib import PurePath

import pytest
import vorta.borg
import vorta.utils
import vorta.views.archive_tab
from PyQt6.QtCore import QDateTime, QItemSelectionModel, Qt
from PyQt6.QtWidgets import QMenu
from vorta.store.models import ArchiveModel
from vorta.views.diff_result import (
    ChangeType,
    DiffData,
    DiffResultDialog,
    DiffTree,
    FileType,
    parse_diff_json,
    parse_diff_lines,
)
from vorta.views.partials.treemodel import FileTreeModel


def setup_diff_result_window(qtbot, mocker, tab, borg_json_output, json_mock_file="diff_archives"):
    """Sets up the diff result window."""
    stdout, stderr = borg_json_output(json_mock_file)
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    compat = vorta.utils.borg_compat

    def check(feature_name):
        if feature_name == 'DIFF_JSON_LINES':
            return False
        return vorta.utils.BorgCompatibility.check(compat, feature_name)

    mocker.patch.object(vorta.utils.borg_compat, 'check', check)

    selection_model: QItemSelectionModel = tab.archiveTable.selectionModel()
    model = tab.archiveTable.model()

    flags = QItemSelectionModel.SelectionFlag.Rows
    flags |= QItemSelectionModel.SelectionFlag.Select

    selection_model.select(model.index(0, 0), flags)
    selection_model.select(model.index(1, 0), flags)

    tab.diff_action()

    qtbot.waitUntil(lambda: hasattr(tab, '_resultwindow'), **pytest._wait_defaults)
    assert hasattr(tab, '_resultwindow')


@pytest.mark.parametrize(
    'json_mock_file, folder_root', [('diff_archives', 'test'), ('diff_archives_dict_issue', 'Users')]
)
def test_archive_diff(qapp, qtbot, mocker, borg_json_output, json_mock_file, folder_root, archive_env):
    """Tests basic functionality of archive diff."""
    main, tab = archive_env
    setup_diff_result_window(qtbot, mocker, tab, borg_json_output, json_mock_file)

    model = tab._resultwindow.treeView.model().sourceModel()
    assert model.root.children[0].subpath == folder_root
    assert tab._resultwindow.archiveNameLabel_1.text() == 'test-archive'
    tab._resultwindow.accept()


def test_diff_item_copy(qapp, qtbot, mocker, borg_json_output, archive_env):
    """Tests copy action by row selection and when passed an index."""
    main, tab = archive_env
    setup_diff_result_window(qtbot, mocker, tab, borg_json_output)

    # mock the clipboard to ensure no changes are made to it during testing
    mocker.patch.object(qapp.clipboard(), "setMimeData")
    clipboard_spy = mocker.spy(qapp.clipboard(), "setMimeData")

    # test 'diff_item_copy()' by passing it an item to copy
    index = tab._resultwindow.treeView.model().index(0, 0)
    assert index is not None
    tab._resultwindow.diff_item_copy(index)
    clipboard_data = clipboard_spy.call_args[0][0]
    assert clipboard_data.hasText()
    assert clipboard_data.text() == "/test"

    clipboard_spy.reset_mock()

    # test 'diff_item_copy()' by selecting a row to copy
    flags = QItemSelectionModel.SelectionFlag.Rows
    flags |= QItemSelectionModel.SelectionFlag.Select
    tab._resultwindow.treeView.selectionModel().select(tab._resultwindow.treeView.model().index(0, 0), flags)
    tab._resultwindow.diff_item_copy()
    clipboard_data = clipboard_spy.call_args[0][0]
    assert clipboard_data.hasText()
    assert clipboard_data.text() == "/test"


def test_treeview_context_menu(qapp, qtbot, mocker, borg_json_output, archive_env):
    """Tests the diff result window context menu for expected actions."""
    main, tab = archive_env
    setup_diff_result_window(qtbot, mocker, tab, borg_json_output)

    # Load the context menu at the first result in window
    pos = tab._resultwindow.treeView.visualRect(tab._resultwindow.treeView.model().index(0, 0)).center()
    tab._resultwindow.treeview_context_menu(pos)
    qtbot.waitUntil(lambda: tab._resultwindow.findChild(QMenu) is not None, **pytest._wait_defaults)
    context_menu = tab._resultwindow.findChild(QMenu)
    assert context_menu is not None

    # assert the actions are available in the context menu
    expected_actions = ['Copy', 'Expand recursively']
    for action in expected_actions:
        assert any(menu_actions.text() == action for menu_actions in context_menu.actions())


@pytest.mark.parametrize(
    'line, expected',
    [
        (
            'changed link        some/changed/link',
            ('some/changed/link', FileType.LINK, ChangeType.CHANGED_LINK, 0, 0, None, None, None, None, None),
        ),
        (
            ' +77.8 kB  -77.8 kB some/changed/file',
            (
                'some/changed/file',
                FileType.FILE,
                ChangeType.MODIFIED,
                2 * 77800,
                0,
                None,
                None,
                None,
                None,
                (77800, 77800),
            ),
        ),
        (
            ' +77.8 kB  -77.8 kB [-rw-rw-rw- -> -rw-r--r--] some/changed/file',
            (
                'some/changed/file',
                FileType.FILE,
                ChangeType.MODIFIED,
                2 * 77800,
                0,
                ('-rw-rw-rw-', '-rw-r--r--'),
                None,
                None,
                None,
                (77800, 77800),
            ),
        ),
        (
            '[-rw-rw-rw- -> -rw-r--r--] some/changed/file',
            (
                'some/changed/file',
                FileType.FILE,
                ChangeType.MODE,
                0,
                0,
                ('-rw-rw-rw-', '-rw-r--r--'),
                None,
                None,
                None,
                None,
            ),
        ),
        (
            'added directory    some/changed/dir',
            ('some/changed/dir', FileType.DIRECTORY, ChangeType.ADDED, 0, 0, None, None, None, None, None),
        ),
        (
            'removed directory  some/changed/dir',
            ('some/changed/dir', FileType.DIRECTORY, ChangeType.REMOVED_DIR, 0, 0, None, None, None, None, None),
        ),
        # Example from https://github.com/borgbase/vorta/issues/521
        (
            '[user:user -> nfsnobody:nfsnobody] home/user/arrays/test.txt',
            (
                'home/user/arrays/test.txt',
                FileType.FILE,
                ChangeType.OWNER,
                0,
                0,
                None,
                ('user', 'user', 'nfsnobody', 'nfsnobody'),
                None,
                None,
                None,
            ),
        ),
        # Very short owner change, to check stripping whitespace from file path
        (
            '[a:a -> b:b]       home/user/arrays/test.txt',
            (
                'home/user/arrays/test.txt',
                FileType.FILE,
                ChangeType.OWNER,
                0,
                0,
                None,
                ('a', 'a', 'b', 'b'),
                None,
                None,
                None,
            ),
        ),
        # All file-related changes in one test
        (
            ' +77.8 kB  -800 B [user:user -> nfsnobody:nfsnobody] [-rw-rw-rw- -> -rw-r--r--] home/user/arrays/test.txt',
            (
                'home/user/arrays/test.txt',
                FileType.FILE,
                ChangeType.OWNER,
                77800 + 800,
                77000,
                ('-rw-rw-rw-', '-rw-r--r--'),
                ('user', 'user', 'nfsnobody', 'nfsnobody'),
                None,
                None,
                (77800, 800),
            ),
        ),
    ],
)
def test_archive_diff_parser(line, expected):
    model = DiffTree()
    model.setMode(model.DisplayMode.FLAT)
    parse_diff_lines([line], model)

    assert model.rowCount() == 1
    item = model.index(0, 0).internalPointer()

    assert item.path == PurePath(expected[0]).parts
    assert item.data == DiffData(*expected[1:])


@pytest.mark.parametrize(
    'line, expected',
    [
        (
            {'path': 'some/changed/link', 'changes': [{'type': 'changed link'}]},
            ('some/changed/link', FileType.LINK, ChangeType.CHANGED_LINK, 0, 0, None, None, None, None, None),
        ),
        (
            {'path': 'some/changed/file', 'changes': [{'type': 'modified', 'added': 77800, 'removed': 77800}]},
            (
                'some/changed/file',
                FileType.FILE,
                ChangeType.MODIFIED,
                2 * 77800,
                0,
                None,
                None,
                None,
                None,
                (77800, 77800),
            ),
        ),
        (
            {
                'path': 'some/changed/file',
                'changes': [
                    {'type': 'modified', 'added': 77800, 'removed': 800},
                    {'type': 'mode', 'old_mode': '-rw-rw-rw-', 'new_mode': '-rw-r--r--'},
                ],
            },
            (
                'some/changed/file',
                FileType.FILE,
                ChangeType.MODIFIED,
                77800 + 800,
                77000,
                ('-rw-rw-rw-', '-rw-r--r--'),
                None,
                None,
                None,
                (77800, 800),
            ),
        ),
        (
            {
                'path': 'some/changed/file',
                'changes': [{'type': 'mode', 'old_mode': '-rw-rw-rw-', 'new_mode': '-rw-r--r--'}],
            },
            (
                'some/changed/file',
                FileType.FILE,
                ChangeType.MODE,
                0,
                0,
                ('-rw-rw-rw-', '-rw-r--r--'),
                None,
                None,
                None,
                None,
            ),
        ),
        (
            {'path': 'some/changed/dir', 'changes': [{'type': 'added directory'}]},
            ('some/changed/dir', FileType.DIRECTORY, ChangeType.ADDED, 0, 0, None, None, None, None, None),
        ),
        (
            {'path': 'some/changed/dir', 'changes': [{'type': 'removed directory'}]},
            ('some/changed/dir', FileType.DIRECTORY, ChangeType.REMOVED_DIR, 0, 0, None, None, None, None, None),
        ),
        # Example from https://github.com/borgbase/vorta/issues/521
        (
            {
                'path': 'home/user/arrays/test.txt',
                'changes': [
                    {
                        'type': 'owner',
                        'old_user': 'user',
                        'new_user': 'nfsnobody',
                        'old_group': 'user',
                        'new_group': 'nfsnobody',
                    }
                ],
            },
            (
                'home/user/arrays/test.txt',
                FileType.FILE,
                ChangeType.OWNER,
                0,
                0,
                None,
                ('user', 'user', 'nfsnobody', 'nfsnobody'),
                None,
                None,
                None,
            ),
        ),
        # Very short owner change, to check stripping whitespace from file path
        (
            {
                'path': 'home/user/arrays/test.txt',
                'changes': [{'type': 'owner', 'old_user': 'a', 'new_user': 'b', 'old_group': 'a', 'new_group': 'b'}],
            },
            (
                'home/user/arrays/test.txt',
                FileType.FILE,
                ChangeType.OWNER,
                0,
                0,
                None,
                ('a', 'a', 'b', 'b'),
                None,
                None,
                None,
            ),
        ),
        # Short ctime change
        (
            {
                'path': 'home/user/arrays',
                'changes': [
                    {
                        'new_ctime': '2023-04-01T17:23:14.104630',
                        'old_ctime': '2023-03-03T23:40:17.073948',
                        'type': 'ctime',
                    }
                ],
            },
            (
                'home/user/arrays',
                FileType.FILE,
                ChangeType.MODIFIED,
                0,
                0,
                None,
                None,
                (
                    QDateTime.fromString('2023-03-03T23:40:17.073948', Qt.DateFormat.ISODateWithMs),
                    QDateTime.fromString('2023-04-01T17:23:14.104630', Qt.DateFormat.ISODateWithMs),
                ),
                None,
                None,
            ),
        ),
        # Short mtime change
        (
            {
                'path': 'home/user/arrays',
                'changes': [
                    {
                        'new_mtime': '2023-04-01T17:23:14.104630',
                        'old_mtime': '2023-03-03T23:40:17.073948',
                        'type': 'mtime',
                    }
                ],
            },
            (
                'home/user/arrays',
                FileType.FILE,
                ChangeType.MODIFIED,
                0,
                0,
                None,
                None,
                None,
                (
                    QDateTime.fromString('2023-03-03T23:40:17.073948', Qt.DateFormat.ISODateWithMs),
                    QDateTime.fromString('2023-04-01T17:23:14.104630', Qt.DateFormat.ISODateWithMs),
                ),
                None,
            ),
        ),
        # All file-related changes in one test
        (
            {
                'path': 'home/user/arrays/test.txt',
                'changes': [
                    {'type': 'modified', 'added': 77800, 'removed': 77800},
                    {'type': 'mode', 'old_mode': '-rw-rw-rw-', 'new_mode': '-rw-r--r--'},
                    {
                        'type': 'owner',
                        'old_user': 'user',
                        'new_user': 'nfsnobody',
                        'old_group': 'user',
                        'new_group': 'nfsnobody',
                    },
                    {
                        'new_ctime': '2023-04-01T17:23:14.104630',
                        'old_ctime': '2023-03-03T23:40:17.073948',
                        'type': 'ctime',
                    },
                    {
                        'new_mtime': '2023-04-01T17:15:50.290565',
                        'old_mtime': '2023-03-05T00:24:00.359045',
                        'type': 'mtime',
                    },
                ],
            },
            (
                'home/user/arrays/test.txt',
                FileType.FILE,
                ChangeType.OWNER,
                2 * 77800,
                0,
                ('-rw-rw-rw-', '-rw-r--r--'),
                ('user', 'user', 'nfsnobody', 'nfsnobody'),
                (
                    QDateTime.fromString('2023-03-03T23:40:17.073948', Qt.DateFormat.ISODateWithMs),
                    QDateTime.fromString('2023-04-01T17:23:14.104630', Qt.DateFormat.ISODateWithMs),
                ),
                (
                    QDateTime.fromString('2023-03-05T00:24:00.359045', Qt.DateFormat.ISODateWithMs),
                    QDateTime.fromString('2023-04-01T17:15:50.290565', Qt.DateFormat.ISODateWithMs),
                ),
                (77800, 77800),
            ),
        ),
    ],
)
def test_archive_diff_json_parser(line, expected):
    model = DiffTree()
    model.setMode(model.DisplayMode.FLAT)
    parse_diff_json([line], model)

    assert model.rowCount() == 1
    item = model.index(0, 0).internalPointer()

    assert item.path == PurePath(expected[0]).parts
    assert item.data == DiffData(*expected[1:])


@pytest.mark.parametrize(
    "selection, expected_mode, expected_bCollapseAllEnabled",
    [
        (0, FileTreeModel.DisplayMode.TREE, True),
        (1, FileTreeModel.DisplayMode.SIMPLIFIED_TREE, True),
        (2, FileTreeModel.DisplayMode.FLAT, False),
    ],
)
def test_change_display_mode(selection: int, expected_mode, expected_bCollapseAllEnabled):
    dialog = DiffResultDialog(ArchiveModel(), ArchiveModel(), DiffTree())
    dialog.change_display_mode(selection)

    assert dialog.model.mode == expected_mode
    assert dialog.bCollapseAll.isEnabled() == expected_bCollapseAllEnabled
