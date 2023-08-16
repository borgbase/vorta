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
        '/tmp/another',
    ]

    default_profile.repo.create_backup_cmd = '--paths-from-command -- echo /tmp/another'
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
        '/tmp/another',
    ]
