"""Exact Borg argv built by each job's prepare(), for Borg 1 and Borg 2."""

import os
import re

import pytest
from PyQt6 import QtCore
from test_constants import TEST_SOURCE_DIR

import vorta.borg.borg_job
import vorta.utils
from vorta.borg.break_lock import BorgBreakJob
from vorta.borg.change_passphrase import BorgChangePassJob
from vorta.borg.check import BorgCheckJob
from vorta.borg.compact import BorgCompactJob
from vorta.borg.create import BorgCreateJob
from vorta.borg.delete import BorgDeleteJob
from vorta.borg.diff import BorgDiffJob
from vorta.borg.extract import BorgExtractJob
from vorta.borg.info_archive import BorgInfoArchiveJob
from vorta.borg.info_repo import BorgInfoRepoJob
from vorta.borg.init import BorgInitJob
from vorta.borg.list_archive import BorgListArchiveJob
from vorta.borg.list_repo import BorgListRepoJob
from vorta.borg.mount import BorgMountJob
from vorta.borg.prune import BorgPruneJob
from vorta.borg.rename import BorgRenameJob
from vorta.store.models import BackupProfileModel, SettingsModel
from vorta.utils import extract_mount_points_v1, extract_mount_points_v2
from vorta.views.dialogs.archive.extract import ExtractTree

URL = 'i0fi93@i593.repo.borgbase.com:repo'
NEW_URL = 'u@h:repo'
B1 = '1.4.3'
B1_OLD = '1.1.18'
B2 = '2.0.0b25'
PRUNE_OPTS = ['--keep-hourly', '2', '--keep-daily', '7', '--keep-weekly', '4', '--keep-monthly', '6']
PRUNE_OPTS += ['--keep-yearly', '2']
LIST_FORMAT = '{mode}{user}{group}{size}{isomtime}{path}{source}{health}{NL}'


@pytest.fixture
def borg_version(monkeypatch):
    def _set(version):
        monkeypatch.setattr(vorta.utils.borg_compat, 'version', version)

    return _set


@pytest.fixture
def profile():
    p = BackupProfileModel.get()
    p.new_archive_name = 'a1'
    p.prune_prefix = 'pfx-'
    return p


def new_repo_params():
    return {
        'repo_url': NEW_URL,
        'repo_name': 'n',
        'extra_borg_arguments': '',
        'ssh_key': None,
        'password': '',
        'encryption': 'none',
    }


def set_override_mount_permissions(value):
    setting = SettingsModel.get(key='override_mount_permissions')
    setting.value = value
    setting.save()


def mount_opts(override):
    return ['-o', f'umask=0277,uid={os.getuid()}'] if override else []


class FakeProc:
    def __init__(self, cmdline):
        self._cmdline = cmdline

    def cmdline(self):
        return self._cmdline


# Sites whose argv is pinned for both Borg 1 and Borg 2.
SHARED_CASES = {
    'create': (
        lambda p: BorgCreateJob.prepare(p),
        {
            B1: ['borg', 'create', '--list', '--progress', '--info', '--log-json', '--json', '--filter=AM']
            + ['-C', 'lz4', f'{URL}::a1', TEST_SOURCE_DIR],
            B2: ['borg', 'create', '--list', '--progress', '--info', '--log-json', '--json', '--filter=AM']
            + ['-C', 'lz4', '-r', URL, 'a1', TEST_SOURCE_DIR],
        },
    ),
    'list_archive': (
        lambda p: BorgListArchiveJob.prepare(p, 'a1'),
        {
            B1: ['borg', 'list', '--info', '--log-json', '--json-lines', '--format', LIST_FORMAT, f'{URL}::a1'],
            B2: ['borg', 'list', '--info', '--log-json', '--json-lines', '--format', LIST_FORMAT, '-r', URL, 'a1'],
        },
    ),
    'rename': (
        lambda p: BorgRenameJob.prepare(p, 'a1', 'a2'),
        {
            B1: ['borg', 'rename', '--info', '--log-json', f'{URL}::a1', 'a2'],
            B2: ['borg', 'rename', '--info', '--log-json', '-r', URL, 'a1', 'a2'],
        },
    ),
    'diff': (
        lambda p: BorgDiffJob.prepare(p, 'a1', 'a2'),
        {
            B1: ['borg', 'diff', '--info', '--log-json', '--json-lines', f'{URL}::a1', 'a2'],
            B2: ['borg', 'diff', '--info', '--log-json', '--json-lines', '-r', URL, 'a1', 'a2'],
        },
    ),
    'check': (
        lambda p: BorgCheckJob.prepare(p),
        {
            B1: ['borg', 'check', '--info', '--log-json', '--progress', URL],
            B2: ['borg', 'check', '--info', '--log-json', '--progress', '-r', URL],
        },
    ),
    'compact': (
        lambda p: BorgCompactJob.prepare(p),
        {
            B1: ['borg', '--info', '--log-json', 'compact', '--progress', URL],
            B2: ['borg', '--info', '--log-json', 'compact', '--progress', '-r', URL],
        },
    ),
    'prune': (
        lambda p: BorgPruneJob.prepare(p),
        {
            B1_OLD: ['borg', 'prune', '--list', '--info', '--log-json']
            + PRUNE_OPTS
            + ['--prefix', 'pfx-', '--keep-within', '10H', URL],
            B1: ['borg', 'prune', '--list', '--info', '--log-json']
            + PRUNE_OPTS
            + ['-a', 'pfx-*', '--keep-within', '10H', URL],
            B2: ['borg', 'prune', '--list', '--info', '--log-json']
            + PRUNE_OPTS
            + ['-a', 'sh:pfx-*', '--keep-within', '10H', '-r', URL],
        },
    ),
    'change_passphrase': (
        lambda p: BorgChangePassJob.prepare(p, 'new-pw'),
        {
            B1: ['borg', '--info', '--log-json', 'key', 'change-passphrase', URL],
            B2: ['borg', '--info', '--log-json', 'key', 'change-passphrase', '-r', URL],
        },
    ),
    'info_repo': (
        lambda p: BorgInfoRepoJob.prepare(new_repo_params()),
        {
            B1: ['borg', 'info', '--info', '--json', '--log-json', NEW_URL],
            B2: ['borg', 'repo-info', '--info', '--json', '--log-json', '-r', NEW_URL],
        },
    ),
    'list_repo': (
        lambda p: BorgListRepoJob.prepare(p),
        {
            B1: ['borg', 'list', '--info', '--log-json', '--json', URL],
            B2: ['borg', 'repo-list', '--info', '--log-json', '--json', '-r', URL],
        },
    ),
    'init': (
        lambda p: BorgInitJob.prepare(new_repo_params()),
        {
            B1: ['borg', 'init', '--info', '--log-json', '--encryption=none', NEW_URL],
            B2: ['borg', 'repo-create', '--info', '--log-json', '--encryption=none', '-r', NEW_URL],
        },
    ),
}

SHARED_PARAMS = [(site, version) for site, (_, expected) in SHARED_CASES.items() for version in expected]


@pytest.mark.parametrize('site,version', SHARED_PARAMS)
def test_shared_argv(site, version, borg_version, profile):
    borg_version(version)
    prepare, expected = SHARED_CASES[site]
    ret = prepare(profile)
    assert ret['ok'], ret.get('message')
    assert ret['cmd'] == expected[version]


@pytest.mark.parametrize(
    'version,expected',
    [
        (B1, ['borg', 'extract', '--list', '--info', '--log-json', f'{URL}::a1']),
        (B2, ['borg', 'extract', '--list', '--info', '--log-json', '-r', URL, 'a1']),
    ],
)
def test_extract_argv(version, expected, borg_version, profile):
    borg_version(version)
    ret = BorgExtractJob.prepare(profile, 'a1', ExtractTree(), '/tmp')
    assert ret['ok']
    # The pattern file name is random.
    assert ret['cmd'][:-2] == expected
    assert ret['cmd'][-2] == '--patterns-from'


def test_info_archive_argv_borg1(borg_version, profile):
    borg_version(B1)
    assert BorgInfoArchiveJob.prepare(profile, 'a1')['cmd'] == ['borg', 'info', '--log-json', '--json', f'{URL}::a1']


def test_break_lock_argv_borg1(borg_version, profile):
    borg_version(B1)
    assert BorgBreakJob.prepare(profile)['cmd'] == ['borg', 'break-lock', '--info', '--log-json', URL]


@pytest.mark.parametrize('override', [False, True])
@pytest.mark.parametrize('archive,source', [(None, URL), ('a*b[c]?', f'{URL}::a*b[c]?')])
def test_mount_argv_borg1(override, archive, source, borg_version, profile):
    borg_version(B1)
    set_override_mount_permissions(override)
    ret = BorgMountJob.prepare(profile, archive)
    assert ret['ok']
    assert ret['cmd'] == ['borg', '--log-json', 'mount'] + mount_opts(override) + [source]


def test_delete_argv_borg1(borg_version, profile):
    borg_version(B1)
    ret = BorgDeleteJob.prepare(profile, ['a', 'b', 'c'])
    assert ret['cmd'] == ['borg', 'delete', '--info', '--log-json', f'{URL}::a', 'b', 'c']


def run_check_from_tab(qtbot, mocker, borg_json_output, archive_env, select_row):
    main, tab = archive_env
    archive_name = None
    if select_row:
        tab.archiveTable.selectRow(0)
        archive_name = tab.selected_archives()[0].name
        assert archive_name in ('test-archive', 'test-archive1')
    stdout, stderr = borg_json_output('check')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    popen = mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    tab.archive_maintenance.check_action()
    qtbot.waitUntil(lambda: popen.called, **pytest._wait_defaults)
    qtbot.waitUntil(lambda: 'Archive consistency check complete' in main.logText.text(), **pytest._wait_defaults)
    qtbot.waitUntil(lambda: not main.app.jobs_manager.is_worker_running(), **pytest._wait_defaults)
    return popen.call_args.args[0][1:], archive_name


def test_check_selected_archive_view_borg1(qapp, qtbot, mocker, borg_json_output, archive_env, borg_version):
    borg_version(B1)
    argv, name = run_check_from_tab(qtbot, mocker, borg_json_output, archive_env, select_row=True)
    assert argv == ['check', '--info', '--log-json', '--progress', f'{URL}::{name}']


@pytest.mark.parametrize(
    'cmdline,expected',
    [
        (['borg', '--log-json', 'mount', f'{URL}::a*b[c]?', '/mnt/a'], ({'a*b[c]?': '/mnt/a'}, [])),
        (
            ['/usr/bin/python3', '/usr/bin/borg', '--log-json', '--lock-wait', '5', 'mount']
            + ['-o', 'umask=0277,uid=501', f'{URL}::a1', '/mnt/a'],
            ({'a1': '/mnt/a'}, []),
        ),
        (['borg', '--log-json', 'mount', URL, '/mnt/repo'], ({}, ['/mnt/repo'])),
        (['borg', '--log-json', 'mount', 'other@host:repo::a1', '/mnt/a'], ({}, [])),
    ],
)
def test_extract_mount_points_v1(cmdline, expected):
    assert extract_mount_points_v1(FakeProc(cmdline), URL) == expected


HELPER_URL = 'ssh://u@h/./repo'
HELPER_ARCHIVES = [None, 'a', 'a*b[c]?', 'sh:x']


def expected_repo_args(version, archive, match):
    if not version.startswith('2.'):
        return [HELPER_URL] if archive is None else [f'{HELPER_URL}::{archive}']
    if archive is None:
        return ['-r', HELPER_URL]
    return ['-r', HELPER_URL, '-a', f'id:{archive}'] if match else ['-r', HELPER_URL, archive]


@pytest.mark.parametrize('match', [False, True])
@pytest.mark.parametrize('archive', HELPER_ARCHIVES)
@pytest.mark.parametrize('version', ['1.1.18', '1.4.3', '2.0.0b10', '2.0.0b25'])
def test_repo_args(version, archive, match, borg_version):
    borg_version(version)
    assert vorta.utils.borg_compat.repo_args(HELPER_URL, archive, match=match) == expected_repo_args(
        version, archive, match
    )


def test_repo_args_literals(borg_version):
    compat = vorta.utils.borg_compat
    borg_version('1.4.3')
    assert compat.repo_args(HELPER_URL, 'sh:x', match=True) == [f'{HELPER_URL}::sh:x']
    borg_version('2.0.0b10')
    assert compat.repo_args(HELPER_URL, 'sh:x', match=True) == ['-r', HELPER_URL, '-a', 'id:sh:x']
    assert compat.repo_args(HELPER_URL, 'a*b[c]?') == ['-r', HELPER_URL, 'a*b[c]?']
    assert compat.match_archive('a*b[c]?') == 'id:a*b[c]?'


# Borg 2 argv after the fixes from #2601.


def test_break_lock_argv_borg2(borg_version, profile):
    borg_version(B2)
    assert BorgBreakJob.prepare(profile)['cmd'] == ['borg', 'break-lock', '--info', '--log-json', '-r', URL]


@pytest.mark.parametrize(
    'archive,expected',
    [
        (None, ['-r', URL]),
        ('', ['-r', URL]),
        ('a*b[c]?', ['-r', URL, '-a', 'id:a*b[c]?']),
    ],
)
def test_check_argv_borg2(archive, expected, borg_version, profile):
    borg_version(B2)
    ret = BorgCheckJob.prepare(profile, archive)
    assert ret['cmd'] == ['borg', 'check', '--info', '--log-json', '--progress'] + expected


def test_check_archive_argv_borg1(borg_version, profile):
    borg_version(B1)
    ret = BorgCheckJob.prepare(profile, 'a*b[c]?')
    assert ret['cmd'] == ['borg', 'check', '--info', '--log-json', '--progress', f'{URL}::a*b[c]?']


@pytest.mark.parametrize('override', [False, True])
@pytest.mark.parametrize('archive,selection', [(None, []), ('a*b[c]?', ['-a', 'id:a*b[c]?'])])
def test_mount_argv_borg2(override, archive, selection, borg_version, profile):
    borg_version(B2)
    set_override_mount_permissions(override)
    ret = BorgMountJob.prepare(profile, archive)
    assert ret['cmd'] == ['borg', '--log-json', 'mount'] + mount_opts(override) + ['-r', URL] + selection
    assert ret.get('mounted_archive') == archive


def test_info_archive_argv_borg2(borg_version, profile):
    borg_version(B2)
    ret = BorgInfoArchiveJob.prepare(profile, 'a*b[c]?')
    assert ret['cmd'] == ['borg', 'info', '--log-json', '--json', '-r', URL, '-a', 'id:a*b[c]?']


def test_delete_argv_borg2(borg_version, profile):
    borg_version(B2)
    names = ['host.local', 'x+y', 'a(b']
    ret = BorgDeleteJob.prepare(profile, names)
    assert ret['cmd'] == ['borg', 'delete', '--info', '--log-json', '-r', URL, '-a', r're:(?:host\.local|x\+y|a\(b)']

    # Borg 2 matches `re:` patterns with re.match and an appended \Z.
    regex = re.compile(ret['cmd'][-1][3:] + r'\Z')
    for name in names:
        assert regex.match(name)
    for name in ['hostXlocal', 'xxy', 'host.local2', 'x+y-old', 'a', '']:
        assert not regex.match(name)


def test_check_selected_archive_view_borg2(qapp, qtbot, mocker, borg_json_output, archive_env, borg_version):
    borg_version(B2)
    argv, name = run_check_from_tab(qtbot, mocker, borg_json_output, archive_env, select_row=True)
    assert argv == ['check', '--info', '--log-json', '--progress', '-r', URL, '-a', f'id:{name}']


def test_check_no_selection_view_borg2(qapp, qtbot, mocker, borg_json_output, archive_env, borg_version):
    borg_version(B2)
    argv, _ = run_check_from_tab(qtbot, mocker, borg_json_output, archive_env, select_row=False)
    assert argv == ['check', '--info', '--log-json', '--progress', '-r', URL]


@pytest.mark.parametrize('returncode', [1, 2])
def test_break_lock_failure_message(returncode, qapp, qtbot, mocker, borg_json_output, borg_version):
    borg_version(B1)
    main = qapp.main_window
    stdout, stderr = borg_json_output('create_break')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=returncode)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    qapp.break_lock(BackupProfileModel.get())

    qtbot.waitUntil(lambda: 'Breaking the repository lock failed' in main.progressText.text(), **pytest._wait_defaults)
    qtbot.waitUntil(lambda: not qapp.jobs_manager.is_worker_running(), **pytest._wait_defaults)
    assert 'lock broken' not in main.progressText.text()


@pytest.mark.parametrize('returncode,text', [(0, 'Repository lock broken'), (2, 'Breaking the repository lock failed')])
def test_break_lock_finished_signals(returncode, text, qapp, mocker, profile):
    params = BorgBreakJob.prepare(profile)
    job = BorgBreakJob(params['cmd'], params)
    result = {'params': params, 'cmd': params['cmd'], 'returncode': returncode, 'errors': [], 'data': {}}
    emitted = []
    slots = {
        'finished': lambda res: emitted.append(('finished', res)),
        'progress': lambda msg: emitted.append(('progress', msg)),
        'result': lambda res: emitted.append(('result', res)),
    }
    qapp.backup_finished_event.connect(slots['finished'], QtCore.Qt.ConnectionType.DirectConnection)
    qapp.backup_progress_event.connect(slots['progress'], QtCore.Qt.ConnectionType.DirectConnection)
    job.result.connect(slots['result'], QtCore.Qt.ConnectionType.DirectConnection)
    try:
        job.finished_event(result)
    finally:
        qapp.backup_finished_event.disconnect(slots['finished'])
        qapp.backup_progress_event.disconnect(slots['progress'])

    assert [name for name, _ in emitted] == ['finished', 'progress', 'result']
    assert emitted[0][1] == result and emitted[2][1] == result
    assert text in emitted[1][1]


V2_MP = '/mnt/point'


@pytest.mark.parametrize(
    'cmdline,expected',
    [
        # Vorta's own shapes
        (['borg', '--log-json', 'mount', '-r', URL, '-a', 'id:a*b[c]?', V2_MP], ({'a*b[c]?': V2_MP}, [])),
        (
            ['borg', '--log-json', 'mount', '-o', 'umask=0277,uid=501', '-r', URL, '-a', 'id:a1', V2_MP],
            ({'a1': V2_MP}, []),
        ),
        (
            ['/usr/bin/python3', '/opt/borg', '--log-json', '--lock-wait', '5', 'mount', '-r', URL, '-a', 'id:a1']
            + [V2_MP],
            ({'a1': V2_MP}, []),
        ),
        (['borg', '--log-json', 'mount', '-r', URL, V2_MP], ({}, [V2_MP])),
        (['borg', '--log-json', 'mount', '-o', 'ro', '-r', URL, V2_MP], ({}, [V2_MP])),
        # Long and joined forms, unprefixed names
        (['borg', 'mount', '--repo', URL, '--match-archives', 'a1', V2_MP], ({'a1': V2_MP}, [])),
        (['borg', 'mount', f'--repo={URL}', '--match-archives=id:a1', V2_MP], ({'a1': V2_MP}, [])),
        (['borg', 'mount', V2_MP, '-r', URL, '-a', 'a1'], ({'a1': V2_MP}, [])),
        # Values of other options and later positionals (paths) are not the mount point
        (['borg', 'mount', '--lock-wait', '5', '-r', URL, V2_MP], ({}, [V2_MP])),
        (['borg', 'mount', '--strip-components=1', '-r', URL, '--first', '2', '-e', 'pat', V2_MP], ({}, [V2_MP])),
        (['borg', 'mount', '-r', URL, V2_MP, 'home/user'], ({}, [V2_MP])),
        # Other repo
        (['borg', 'mount', '-r', 'other@host:repo', '-a', 'id:a1', V2_MP], ({}, [])),
        (['borg', 'mount', '-r', 'other@host:repo', V2_MP], ({}, [])),
        (['borg', 'mount', f'{URL}::a1', V2_MP], ({}, [])),
        # Foreign pattern prefixes are not archive names
        (['borg', 'mount', '-r', URL, '-a', 'sh:a*', V2_MP], ({}, [])),
        (['borg', 'mount', '-r', URL, '-a', 're:a.*', V2_MP], ({}, [])),
        (['borg', 'mount', '-r', URL, '-a', 'aid:1234', V2_MP], ({}, [])),
        (['borg', 'mount', '-r', URL, '-a', 'name:a1', V2_MP], ({}, [])),
        (['borg', 'mount', '-r', URL, '-a', 'host:h', V2_MP], ({}, [])),
        (['borg', 'mount', '-r', URL, '-a', 'user:u', V2_MP], ({}, [])),
        (['borg', 'mount', '-r', URL, '-a', 'tags:t', V2_MP], ({}, [])),
        (['borg', 'mount', '-r', URL, '-a', 'date:today', V2_MP], ({}, [])),
        # Truncated or odd command lines
        (['borg', 'mount'], ({}, [])),
        (['borg', 'mount', '-r'], ({}, [])),
        (['borg', 'mount', '-r', URL], ({}, [])),
        (['borg', 'mount', '-r', URL, '-a'], ({}, [])),
        (['borg', 'mount', '-r', URL, '-a', 'id:a1'], ({}, [])),
        (['borg', 'mount', '-o'], ({}, [])),
        (['borg', 'mount', '-r', URL, '-a', 'id:a1', '-a', 'id:a2', V2_MP], ({'a2': V2_MP}, [])),
        (['python3', '-m', 'http.server'], ({}, [])),
        ([], ({}, [])),
    ],
)
def test_extract_mount_points_v2(cmdline, expected):
    assert extract_mount_points_v2(FakeProc(cmdline), URL) == expected


@pytest.mark.parametrize('archive', ['a*b[c]?', 'id:x'])
@pytest.mark.parametrize('prefix', [['/usr/local/bin/borg'], ['/usr/bin/python3', '/usr/local/bin/borg']])
@pytest.mark.parametrize('override', [False, True])
def test_mount_round_trip_borg2(archive, prefix, override, borg_version, profile):
    borg_version(B2)
    set_override_mount_permissions(override)
    cmd = BorgMountJob.prepare(profile, archive)['cmd']
    # BorgJob replaces the binary and inserts extra args at cmd[2:]; the view appends the mount point.
    cmd = prefix + cmd[1:2] + ['--lock-wait', '5'] + cmd[2:] + [V2_MP]
    assert extract_mount_points_v2(FakeProc(cmd), URL) == ({archive: V2_MP}, [])


def test_mount_round_trip_repo_borg2(borg_version, profile):
    borg_version(B2)
    cmd = BorgMountJob.prepare(profile)['cmd'] + [V2_MP]
    assert extract_mount_points_v2(FakeProc(cmd), URL) == ({}, [V2_MP])
