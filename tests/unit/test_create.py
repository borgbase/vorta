from test_constants import TEST_SOURCE_DIR

from vorta.borg.create import BorgCreateJob
from vorta.store.models import BackupProfileModel, SourceFileModel


def test_create_paths_from_command():
    default_profile = BackupProfileModel.get()
    default_profile.new_archive_name = 'a1'

    default_profile.repo.create_backup_cmd = '--one-file-system'
    result = BorgCreateJob.prepare(default_profile)

    assert 'cmd' in result
    assert result['cmd'] == [
        'borg',
        'create',
        '--list',
        '--progress',
        '--info',
        '--log-json',
        '--json',
        '--filter=AM',
        '-C',
        'lz4',
        '--one-file-system',
        'i0fi93@i593.repo.borgbase.com:repo::a1',
        TEST_SOURCE_DIR,
    ]

    default_profile.repo.create_backup_cmd = f'--paths-from-command -- echo {TEST_SOURCE_DIR}'
    SourceFileModel.delete().execute()

    result = BorgCreateJob.prepare(default_profile)

    assert 'cmd' in result
    assert result['cmd'] == [
        'borg',
        'create',
        '--list',
        '--progress',
        '--info',
        '--log-json',
        '--json',
        '--filter=AM',
        '-C',
        'lz4',
        '--paths-from-command',
        'i0fi93@i593.repo.borgbase.com:repo::a1',
        '--',
        'echo',
        TEST_SOURCE_DIR,
    ]


def test_prepare_returns_info_level_when_wifi_disallowed(mocker):
    """Test that prepare() returns level='info' when WiFi is not allowed."""
    default_profile = BackupProfileModel.get()
    mock_monitor = mocker.MagicMock()
    mock_monitor.get_current_wifi.return_value = 'blocked_wifi'
    mocker.patch('vorta.borg.create.get_network_status_monitor', return_value=mock_monitor)
    mocker.patch(
        'vorta.borg.create.WifiSettingModel.select',
        return_value=mocker.MagicMock(where=lambda *a, **kw: mocker.MagicMock(count=lambda: 1)),
    )
    result = BorgCreateJob.prepare(default_profile)
    assert result.get('level') == 'info'


def test_prepare_returns_info_level_when_metered_connection(mocker):
    """Test that prepare() returns level='info' for metered connections."""
    default_profile = BackupProfileModel.get()
    default_profile.dont_run_on_metered_networks = True
    mock_monitor = mocker.MagicMock()
    mock_monitor.get_current_wifi.return_value = None
    mock_monitor.is_network_metered.return_value = True
    mocker.patch('vorta.borg.create.get_network_status_monitor', return_value=mock_monitor)
    result = BorgCreateJob.prepare(default_profile)
    assert result.get('level') == 'info'
