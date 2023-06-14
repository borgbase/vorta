import pytest
import vorta.borg
import vorta.utils
import vorta.views.archive_tab
from vorta.borg.diff import BorgDiffJob
from vorta.views.diff_result import (
    ChangeType,
    DiffTree,
    FileType,
    ParseThread,
)


@pytest.mark.parametrize(
    'archive_name_1, archive_name_2, expected',
    [
        (
            'test-archive1',
            'test-archive2',
            [
                {
                    'subpath': 'dir',
                    'data': {
                        'file_type': FileType.FILE,
                        'change_type': ChangeType.MODIFIED,
                        # 'changed_size': 0,
                        # 'size': 0,
                        # 'mode_change': None,
                        # 'owner_change': None,
                        # 'ctime_change': None,
                        # 'mtime_change': None,
                        'modified': None,
                    },
                },
                {
                    'subpath': 'file',
                    'data': {
                        'file_type': FileType.FILE,
                        'change_type': ChangeType.MODIFIED,
                        'modified': (0, 0),
                    },
                },
                {
                    'subpath': 'chrdev',
                    'data': {
                        'file_type': FileType.CHRDEV,
                        'change_type': ChangeType.ADDED,
                        'modified': None,
                    },
                },
                {
                    'subpath': 'fifo',
                    'data': {
                        'file_type': FileType.FIFO,
                        'change_type': ChangeType.ADDED,
                        'modified': None,
                    },
                },
                {
                    'subpath': 'hardlink',
                    'data': {
                        'file_type': FileType.FILE,
                        'change_type': ChangeType.ADDED,
                        'modified': None,
                    },
                },
                {
                    'subpath': 'symlink',
                    'data': {
                        'file_type': FileType.LINK,
                        'change_type': ChangeType.ADDED,
                        'modified': None,
                    },
                },
            ],
        ),
        (
            'test-archive2',
            'test-archive3',
            [
                {
                    'subpath': 'borg_src1',
                    'data': {
                        # TODO: Check/Review why file_type is FILE instead of DIRECTORY
                        'file_type': FileType.FILE,
                        'change_type': ChangeType.MODIFIED,
                        'modified': None,
                    },
                },
                {
                    'subpath': 'dir',
                    'data': {
                        'file_type': FileType.DIRECTORY,
                        'change_type': ChangeType.REMOVED,
                        'modified': None,
                    },
                },
                {
                    'subpath': 'chrdev',
                    'data': {
                        'file_type': FileType.CHRDEV,
                        'change_type': ChangeType.REMOVED,
                    },
                },
                {
                    'subpath': 'fifo',
                    'data': {
                        'file_type': FileType.FIFO,
                        'change_type': ChangeType.REMOVED,
                    },
                },
                {
                    'subpath': 'file',
                    'data': {
                        'file_type': FileType.FILE,
                        'change_type': ChangeType.REMOVED,
                    },
                },
                {
                    'subpath': 'hardlink',
                    'data': {
                        'file_type': FileType.FILE,
                        'change_type': ChangeType.REMOVED,
                    },
                },
                {
                    'subpath': 'symlink',
                    'data': {
                        'file_type': FileType.LINK,
                        'change_type': ChangeType.REMOVED,
                    },
                },
                {
                    'subpath': 'dir1',
                    'data': {
                        'file_type': FileType.DIRECTORY,
                        'change_type': ChangeType.ADDED,
                    },
                },
                {
                    'subpath': 'chrdev',
                    'data': {
                        'file_type': FileType.CHRDEV,
                        'change_type': ChangeType.ADDED,
                    },
                },
                {
                    'subpath': 'fifo',
                    'data': {
                        'file_type': FileType.FIFO,
                        'change_type': ChangeType.ADDED,
                    },
                },
                {
                    'subpath': 'file',
                    'data': {
                        'file_type': FileType.FILE,
                        'change_type': ChangeType.ADDED,
                    },
                },
                {
                    'subpath': 'hardlink',
                    'data': {
                        'file_type': FileType.FILE,
                        'change_type': ChangeType.ADDED,
                    },
                },
                {
                    'subpath': 'symlink',
                    'data': {
                        'file_type': FileType.LINK,
                        'change_type': ChangeType.ADDED,
                    },
                },
            ],
        ),
        (
            'test-archive3',
            'test-archive4',
            [
                {
                    'subpath': 'dir1',
                    'data': {
                        'file_type': FileType.FILE,
                        'change_type': ChangeType.MODIFIED,
                    },
                },
                {
                    'subpath': 'chrdev',
                    'data': {
                        'file_type': FileType.CHRDEV,
                        'change_type': ChangeType.REMOVED,
                    },
                },
                {
                    'subpath': 'chrdev1',
                    'data': {
                        'file_type': FileType.CHRDEV,
                        'change_type': ChangeType.ADDED,
                    },
                },
                {
                    'subpath': 'fifo',
                    'data': {
                        'file_type': FileType.FIFO,
                        'change_type': ChangeType.REMOVED,
                    },
                },
                {
                    'subpath': 'fifo1',
                    'data': {
                        'file_type': FileType.FIFO,
                        'change_type': ChangeType.ADDED,
                    },
                },
                {
                    'subpath': 'file',
                    'data': {
                        'file_type': FileType.FILE,
                        'change_type': ChangeType.REMOVED,
                    },
                },
                {
                    'subpath': 'file1',
                    'data': {
                        'file_type': FileType.FILE,
                        'change_type': ChangeType.ADDED,
                    },
                },
                {
                    'subpath': 'hardlink',
                    'data': {
                        'file_type': FileType.FILE,
                        'change_type': ChangeType.REMOVED,
                    },
                },
                {
                    'subpath': 'hardlink1',
                    'data': {
                        'file_type': FileType.FILE,
                        'change_type': ChangeType.ADDED,
                    },
                },
                {
                    'subpath': 'symlink',
                    'data': {
                        'file_type': FileType.LINK,
                        'change_type': ChangeType.REMOVED,
                    },
                },
                {
                    'subpath': 'symlink1',
                    'data': {
                        'file_type': FileType.LINK,
                        'change_type': ChangeType.ADDED,
                    },
                },
            ],
        ),
        (
            'test-archive4',
            'test-archive5',
            [
                {
                    'subpath': 'dir1',
                    'data': {
                        'file_type': FileType.FILE,
                        'change_type': ChangeType.MODIFIED,
                    },
                },
                {
                    'subpath': 'chrdev1',
                    'data': {
                        'file_type': FileType.CHRDEV,
                        'change_type': ChangeType.REMOVED,
                    },
                },
                {
                    'subpath': 'fifo1',
                    'data': {
                        'file_type': FileType.FIFO,
                        'change_type': ChangeType.REMOVED,
                    },
                },
                {
                    'subpath': 'file1',
                    'data': {
                        'file_type': FileType.FILE,
                        'change_type': ChangeType.REMOVED,
                    },
                },
                {
                    'subpath': 'hardlink1',
                    'data': {
                        'file_type': FileType.FILE,
                        'change_type': ChangeType.REMOVED,
                    },
                },
                {
                    'subpath': 'symlink1',
                    'data': {
                        'file_type': FileType.LINK,
                        'change_type': ChangeType.REMOVED,
                    },
                },
            ],
        ),
        (
            'test-archive5',
            'test-archive6',
            [
                {
                    'subpath': 'dir1',
                    'data': {
                        'file_type': FileType.FILE,
                        'change_type': ChangeType.MODIFIED,
                    },
                },
            ],
        ),
    ],
)
def test_archive_diff_lines(qapp, qtbot, archive_name_1, archive_name_2, expected):
    params = BorgDiffJob.prepare(vorta.store.models.BackupProfileModel.select().first(), archive_name_1, archive_name_2)
    thread = BorgDiffJob(params['cmd'], params, qapp)

    with qtbot.waitSignal(thread.result, **pytest._wait_defaults) as blocker:
        blocker.connect(thread.updated)
        thread.run()

    diff_lines = blocker.args[0]['data']
    json_lines = blocker.args[0]['params']['json_lines']

    model = DiffTree()
    model.setMode(model.DisplayMode.FLAT)

    # Use ParseThread to parse the diff lines
    parse_thread = ParseThread(diff_lines, json_lines, model)
    parse_thread.start()
    qtbot.waitUntil(lambda: parse_thread.isFinished(), **pytest._wait_defaults)

    assert model.rowCount() == len(expected)

    for index, item in enumerate(expected):
        assert model.index(index, 0).internalPointer().subpath == item['subpath']

        # Checking all attributes for every line will produce very large testing output and will be difficult to debug
        # So we will check only the attributes we are interested in
        # TODO: Remove below line above code review
        # assert model.index(index, 0).internalPointer().data == DiffData(**item['data'])

        for key, value in item['data'].items():
            assert getattr(model.index(index, 0).internalPointer().data, key) == value
