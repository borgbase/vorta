import pytest
import vorta.borg
import vorta.views.archive_tab
import vorta.utils


@pytest.mark.parametrize('json_mock_file,folder_root', [
    ('diff_archives', 'test'), ('diff_archives_dict_issue', 'Users')])
def test_archive_diff(qapp, qtbot, mocker, borg_json_output, json_mock_file, folder_root):
    main = qapp.main_window
    tab = main.archiveTab
    main.tabWidget.setCurrentIndex(3)

    tab.populate_from_profile()
    qtbot.waitUntil(lambda: tab.archiveTable.rowCount() == 2)

    stdout, stderr = borg_json_output(json_mock_file)
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_thread, 'Popen', return_value=popen_result)

    tab.diff_action()
    qtbot.waitUntil(lambda: hasattr(tab, '_window'), **pytest._wait_defaults)

    tab._window.archiveTable.selectRow(0)
    tab._window.archiveTable.selectRow(1)
    tab._window.diff_action()
    qtbot.waitUntil(lambda: hasattr(tab, '_resultwindow'), **pytest._wait_defaults)

    assert tab._resultwindow.treeView.model().rootItem.childItems[0].data(0) == folder_root
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


@pytest.mark.parametrize('line, expected', [
    ({'path': 'some/changed/link', 'changes': [{'type': 'changed link'}]},
     (0, 'changed', 'link', 'some/changed')),
    ({'path': 'some/changed/file', 'changes': [{'type': 'modified', 'added': 77800, 'removed': 77800}]},
     (77800, 'modified', 'file', 'some/changed')),
    ({'path': 'some/changed/file', 'changes': [{'type': 'modified', 'added': 77800, 'removed': 77800},
                                               {'type': 'mode', 'old_mode': '-rw-rw-rw-', 'new_mode': '-rw-r--r--'}]},
     (77800, '[-rw-rw-rw- -> -rw-r--r--]', 'file', 'some/changed')),
    ({'path': 'some/changed/file', 'changes': [{'type': 'mode', 'old_mode': '-rw-rw-rw-', 'new_mode': '-rw-r--r--'}]},
     (0, '[-rw-rw-rw- -> -rw-r--r--]', 'file', 'some/changed')),
    ({'path': 'some/changed/dir', 'changes': [{'type': 'added directory'}]},
     (0, 'added', 'dir', 'some/changed')),
    ({'path': 'some/changed/dir', 'changes': [{'type': 'removed directory'}]},
     (0, 'removed', 'dir', 'some/changed')),

    # Example from https://github.com/borgbase/vorta/issues/521
    ({'path': 'home/user/arrays/test.txt', 'changes': [{'type': 'owner', 'old_user': 'user', 'new_user': 'nfsnobody',
                                                        'old_group': 'user', 'new_group': 'nfsnobody'}]},
     (0, 'modified', 'test.txt', 'home/user/arrays')),

    # Very short owner change, to check stripping whitespace from file path
    ({'path': 'home/user/arrays/test.txt', 'changes': [{'type': 'owner', 'old_user': 'a', 'new_user': 'b',
                                                        'old_group': 'a', 'new_group': 'b'}]},
     (0, 'modified', 'test.txt', 'home/user/arrays')),

    # All file-related changes in one test
    ({'path': 'home/user/arrays/test.txt', 'changes': [{'type': 'modified', 'added': 77800, 'removed': 77800},
                                                       {'type': 'mode', 'old_mode': '-rw-rw-rw-',
                                                        'new_mode': '-rw-r--r--'},
                                                       {'type': 'owner', 'old_user': 'user', 'new_user': 'nfsnobody',
                                                        'old_group': 'user', 'new_group': 'nfsnobody'}]},
     (77800, '[-rw-rw-rw- -> -rw-r--r--]', 'test.txt', 'home/user/arrays')),
])
def test_archive_diff_json_parser(line, expected):
    files_with_attributes, _nested_file_list = vorta.views.diff_result.parse_diff_json_lines([line])
    assert files_with_attributes == [expected]
