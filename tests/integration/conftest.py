import os
import subprocess

import pytest
import vorta
import vorta.application
import vorta.borg.jobs_manager
from peewee import SqliteDatabase
from pkg_resources import parse_version
from vorta.store.models import (
    ArchiveModel,
    BackupProfileModel,
    EventLogModel,
    RepoModel,
    RepoPassword,
    SchemaVersion,
    SettingsModel,
    SourceFileModel,
    WifiSettingModel,
)
from vorta.utils import borg_compat
from vorta.views.main_window import ArchiveTab, MainWindow

models = [
    RepoModel,
    RepoPassword,
    BackupProfileModel,
    SourceFileModel,
    SettingsModel,
    ArchiveModel,
    WifiSettingModel,
    EventLogModel,
    SchemaVersion,
]


@pytest.fixture(scope='function', autouse=True)
def borg_version():
    borg_version = os.getenv('BORG_VERSION')
    if not borg_version:
        borg_version = subprocess.run(['borg', '--version'], stdout=subprocess.PIPE).stdout.decode('utf-8')
        borg_version = borg_version.split(' ')[1]

    # test window does not automatically set borg version
    borg_compat.set_version(borg_version, borg_compat.path)

    parsed_borg_version = parse_version(borg_version)
    return borg_version, parsed_borg_version


@pytest.fixture(scope='function', autouse=True)
def create_test_repo(tmpdir_factory, borg_version):
    repo_path = tmpdir_factory.mktemp('repo')
    source_files_dir = tmpdir_factory.mktemp('borg_src')

    is_borg_v2 = borg_version[1] >= parse_version('2.0.0b1')

    if is_borg_v2:
        subprocess.run(['borg', '-r', str(repo_path), 'rcreate', '--encryption=none'], check=True)
    else:
        subprocess.run(['borg', 'init', '--encryption=none', str(repo_path)], check=True)

    def create_archive(timestamp, name):
        if is_borg_v2:
            subprocess.run(
                ['borg', '-r', str(repo_path), 'create', '--timestamp', timestamp, name, str(source_files_dir)],
                cwd=str(repo_path),
                check=True,
            )
        else:
            subprocess.run(
                ['borg', 'create', '--timestamp', timestamp, f'{repo_path}::{name}', str(source_files_dir)],
                cwd=str(repo_path),
                check=True,
            )

    # /src/file
    file_path = os.path.join(source_files_dir, 'file')
    with open(file_path, 'w') as f:
        f.write('test')

    # /src/dir/
    dir_path = os.path.join(source_files_dir, 'dir')
    os.mkdir(dir_path)

    # /src/dir/file
    file_path = os.path.join(dir_path, 'file')
    with open(file_path, 'w') as f:
        f.write('test')

    # Create first archive
    create_archive('2023-06-14T01:00:00', 'test-archive1')

    # /src/dir/symlink
    symlink_path = os.path.join(dir_path, 'symlink')
    os.symlink(file_path, symlink_path)

    # /src/dir/hardlink
    hardlink_path = os.path.join(dir_path, 'hardlink')
    os.link(file_path, hardlink_path)

    # /src/dir/fifo
    fifo_path = os.path.join(dir_path, 'fifo')
    os.mkfifo(fifo_path)

    # /src/dir/chrdev
    supports_chrdev = True
    try:
        chrdev_path = os.path.join(dir_path, 'chrdev')
        os.mknod(chrdev_path, mode=0o600 | 0o020000)
    except PermissionError:
        supports_chrdev = False

    create_archive('2023-06-14T02:00:00', 'test-archive2')

    # Rename dir to dir1
    os.rename(dir_path, os.path.join(source_files_dir, 'dir1'))

    create_archive('2023-06-14T03:00:00', 'test-archive3')

    # Rename all files under dir1
    for file in os.listdir(os.path.join(source_files_dir, 'dir1')):
        os.rename(os.path.join(source_files_dir, 'dir1', file), os.path.join(source_files_dir, 'dir1', file + '1'))

    create_archive('2023-06-14T04:00:00', 'test-archive4')

    # Delete all file under dir1
    for file in os.listdir(os.path.join(source_files_dir, 'dir1')):
        os.remove(os.path.join(source_files_dir, 'dir1', file))

    create_archive('2023-06-14T05:00:00', 'test-archive5')

    # change permission of dir1
    os.chmod(os.path.join(source_files_dir, 'dir1'), 0o700)

    create_archive('2023-06-14T06:00:00', 'test-archive6')

    return repo_path, source_files_dir, supports_chrdev


@pytest.fixture(scope='function', autouse=True)
def init_db(qapp, qtbot, tmpdir_factory, create_test_repo):
    tmp_db = tmpdir_factory.mktemp('Vorta').join('settings.sqlite')
    mock_db = SqliteDatabase(
        str(tmp_db),
        pragmas={
            'journal_mode': 'wal',
        },
    )
    vorta.store.connection.init_db(mock_db)

    default_profile = BackupProfileModel(name='Default')
    default_profile.save()

    repo_path, source_dir, _ = create_test_repo

    new_repo = RepoModel(url=repo_path)
    new_repo.encryption = 'none'
    new_repo.save()

    default_profile.repo = new_repo.id
    default_profile.dont_run_on_metered_networks = False
    default_profile.validation_on = False
    default_profile.save()

    source_dir = SourceFileModel(dir=source_dir, repo=new_repo, dir_size=12, dir_files_count=3, path_isdir=True)
    source_dir.save()

    qapp.main_window.deleteLater()
    del qapp.main_window
    qapp.main_window = MainWindow(qapp)  # Re-open main window to apply mock data in UI

    qapp.scheduler.schedule_changed.disconnect()

    yield

    qapp.jobs_manager.cancel_all_jobs()
    qapp.backup_finished_event.disconnect()
    qtbot.waitUntil(lambda: not qapp.jobs_manager.is_worker_running(), **pytest._wait_defaults)
    mock_db.close()


@pytest.fixture
def choose_file_dialog(tmpdir):
    class MockFileDialog:
        def __init__(self, *args, **kwargs):
            self.directory = kwargs.get('directory', None)
            self.subdirectory = kwargs.get('subdirectory', None)

        def open(self, func):
            func()

        def selectedFiles(self):
            if self.subdirectory:
                return [str(tmpdir.join(self.subdirectory))]
            elif self.directory:
                return [str(self.directory)]
            else:
                return [str(tmpdir)]

    return MockFileDialog


@pytest.fixture
def rootdir():
    return os.path.dirname(os.path.abspath(__file__))


@pytest.fixture()
def archive_env(qapp, qtbot):
    """
    Common setup for integration tests involving the archive tab.
    """
    main: MainWindow = qapp.main_window
    tab: ArchiveTab = main.archiveTab
    main.tabWidget.setCurrentIndex(3)
    tab.refresh_archive_list()
    qtbot.waitUntil(lambda: tab.archiveTable.rowCount() > 0, **pytest._wait_defaults)
    return main, tab


@pytest.fixture(autouse=True)
def min_borg_version(borg_version, request):
    if request.node.get_closest_marker('min_borg_version'):
        parsed_borg_version = borg_version[1]

        if parsed_borg_version < parse_version(request.node.get_closest_marker('min_borg_version').args[0]):
            pytest.skip(
                'skipped due to borg version requirement for test: {}'.format(
                    request.node.get_closest_marker('min_borg_version').args[0]
                )
            )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "min_borg_version(): set minimum required borg version for a test",
    )
