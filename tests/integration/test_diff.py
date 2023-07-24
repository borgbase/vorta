"""
These tests compare the output of the diff command with the expected output.
"""

import pytest
import vorta.borg
import vorta.utils
import vorta.views.archive_tab
from pkg_resources import parse_version
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
                        'modified': None,
                    },
                    'min_version': '1.2.4',
                    'max_version': '1.2.4',
                },
                {
                    'subpath': 'file',
                    'data': {
                        'file_type': FileType.FILE,
                        'change_type': ChangeType.MODIFIED,
                        'modified': (0, 0),
                    },
                    'min_version': '1.2.4',
                    'max_version': '1.2.4',
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
                    'subpath': 'borg_src',
                    'match_startsWith': True,
                    'data': {
                        'file_type': FileType.FILE,
                        'change_type': ChangeType.MODIFIED,
                        'modified': None,
                    },
                    'min_version': '1.2.4',
                    'max_version': '1.2.4',
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
                    'min_version': '1.2.4',
                    'max_version': '1.2.4',
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
                    'min_version': '1.2.4',
                    'max_version': '1.2.4',
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
                    'min_version': '1.2.4',
                    'max_version': '1.2.4',
                },
            ],
        ),
    ],
)
def test_archive_diff_lines(qapp, qtbot, borg_version, create_test_repo, archive_name_1, archive_name_2, expected):
    """Test that the diff lines are parsed correctly for supported borg versions"""
    parsed_borg_version = borg_version[1]
    supports_fifo = parsed_borg_version > parse_version('1.1.18')
    supports_chrdev = create_test_repo[2]

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

    expected = [
        item
        for item in expected
        if (
            ('min_version' not in item or parse_version(item['min_version']) <= parsed_borg_version)
            and ('max_version' not in item or parse_version(item['max_version']) >= parsed_borg_version)
            and (item['data']['file_type'] != FileType.FIFO or supports_fifo)
            and (item['data']['file_type'] != FileType.CHRDEV or supports_chrdev)
        )
    ]

    # diff versions of borg produce inconsistent ordering of diff lines so we sort the expected and model
    expected = sorted(expected, key=lambda item: item['subpath'])
    sorted_model = sorted(
        [model.index(index, 0).internalPointer() for index in range(model.rowCount())],
        key=lambda item: item.subpath,
    )

    assert len(sorted_model) == len(expected)

    for index, item in enumerate(expected):
        if 'match_startsWith' in item and item['match_startsWith']:
            assert sorted_model[index].subpath.startswith(item['subpath'])
        else:
            assert sorted_model[index].subpath == item['subpath']

        for key, value in item['data'].items():
            assert getattr(sorted_model[index].data, key) == value
