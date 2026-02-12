import pytest

import vorta.borg.export_tar
from vorta.borg.export_tar import BorgExportTar
from vorta.store.models import BackupProfileModel


def test_export_tar_prepare(mocker):
    profile = BackupProfileModel.get()

    # Mock borg_compat to control Vversion check
    def side_effect_v2(arg):
        return True

    mocker.patch('vorta.utils.borg_compat.check', side_effect=side_effect_v2)

    # Case 1: Simple export
    result = BorgExportTar.prepare(profile, archive_name='myarchive', destination_file='/tmp/export.tar')

    assert result['ok'] is True
    assert result['cmd'] == ['borg', 'export-tar', '-r', profile.repo.url, 'myarchive', '/tmp/export.tar']

    # Case 2: Compression and strip-components
    result = BorgExportTar.prepare(
        profile, archive_name='myarchive', destination_file='/tmp/export.tar.gz', compression='gzip', strip_components=2
    )

    assert result['ok'] is True
    expected_args = [
        '--tar-filter=gzip',
        '--strip-components=2',
        '-r',
        profile.repo.url,
        'myarchive',
        '/tmp/export.tar.gz',
    ]
    # Check that expected args are present in the command
    for arg in expected_args:
        assert arg in result['cmd']


def test_export_tar_prepare_v1(mocker):
    profile = BackupProfileModel.get()

    # Mock checks for V1
    def side_effect_v1(arg):
        if arg == 'V2':
            return False
        return True  # JSON_LOG must be True

    mocker.patch('vorta.utils.borg_compat.check', side_effect=side_effect_v1)

    result = BorgExportTar.prepare(profile, archive_name='myarchive', destination_file='/tmp/export.tar')

    expected_repo_archive = f"{profile.repo.url}::myarchive"
    assert result['cmd'] == ['borg', 'export-tar', expected_repo_archive, '/tmp/export.tar']


def test_export_tar_prepare_advanced(mocker):
    profile = BackupProfileModel.get()

    # Mock V2 for format support
    mocker.patch('vorta.utils.borg_compat.check', return_value=True)

    result = BorgExportTar.prepare(
        profile,
        archive_name='myarchive',
        destination_file='/tmp/export.tar',
        paths=['path/to/include', 'another/path'],
        excludes=['*.tmp', 'cache/'],
        tar_format='PAX',
    )

    assert result['ok'] is True
    cmd = result['cmd']

    assert '--tar-format=PAX' in cmd
    assert '-e' in cmd
    assert '*.tmp' in cmd
    # Check that paths are at the end
    assert 'path/to/include' in cmd
    assert 'another/path' in cmd
