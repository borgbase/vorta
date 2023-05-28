import atexit
import os
import shutil
import subprocess
import sys

import pytest
import vorta
import vorta.application
import vorta.borg.jobs_manager
from peewee import SqliteDatabase
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
from vorta.views.main_window import MainWindow

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


def pytest_configure(config):
    sys._called_from_test = True
    pytest._wait_defaults = {'timeout': 20000}
    os.environ['LANG'] = 'en'  # Ensure we test an English UI


@pytest.fixture(scope='session')
def qapp(tmpdir_factory):
    # DB is required to init QApplication. New DB used for every test.
    tmp_db = tmpdir_factory.mktemp('Vorta').join('settings.sqlite')
    mock_db = SqliteDatabase(str(tmp_db))
    vorta.store.connection.init_db(mock_db)

    # Needs to be disabled before calling VortaApp()
    if sys.platform == 'darwin':
        cfg = vorta.store.models.SettingsModel.get(key='check_full_disk_access')
        cfg.value = False
        cfg.save()

    from vorta.application import VortaApp

    qapp = VortaApp([])  # Only init QApplication once to avoid segfaults while testing.

    yield qapp
    mock_db.close()
    qapp.quit()


@pytest.fixture(scope='function', autouse=True)
def create_test_repo(tmpdir_factory):
    temp_dir = tmpdir_factory.mktemp('repo')
    repo_path = str(temp_dir)

    subprocess.run(['borg', 'init', '--encryption=none', repo_path], check=True)

    # create source files dir
    source_files_dir = os.path.join(temp_dir, 'src')
    os.mkdir(source_files_dir)

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
    subprocess.run(['borg', 'create', f'{repo_path}::test-archive1', source_files_dir], cwd=temp_dir, check=True)

    # /src/dir/symlink
    symlink_path = os.path.join(dir_path, 'symlink')
    os.symlink(file_path, symlink_path)

    # /src/dir/hardlink
    hardlink_path = os.path.join(dir_path, 'hardlink')
    os.link(file_path, hardlink_path)

    # /src/dir/fifo
    fifo_path = os.path.join(dir_path, 'fifo')
    os.mkfifo(fifo_path)

    # /src/dir/socket
    socket_path = os.path.join(dir_path, 'socket')
    os.mknod(socket_path, mode=0o600 | 0o140000)

    # /src/dir/chrdev
    chrdev_path = os.path.join(dir_path, 'chrdev')
    os.mknod(chrdev_path, mode=0o600 | 0o020000)

    # /src/dir/blkdev
    # blkdev_path = os.path.join(dir_path, 'blkdev')
    # os.mknod(blkdev_path, mode=0o600 | 0o060000)

    # Create second archive
    subprocess.run(['borg', 'create', f'{repo_path}::test-archive2', source_files_dir], cwd=temp_dir, check=True)

    # Rename dir to dir1
    os.rename(dir_path, os.path.join(source_files_dir, 'dir1'))

    subprocess.run(['borg', 'create', f'{repo_path}::test-archive3', source_files_dir], cwd=temp_dir, check=True)

    # Rename all files under dir1 
    for file in os.listdir(os.path.join(source_files_dir, 'dir1')):
        os.rename(os.path.join(source_files_dir, 'dir1', file), os.path.join(source_files_dir, 'dir1', file + '1'))

    subprocess.run(['borg', 'create', f'{repo_path}::test-archive4', source_files_dir], cwd=temp_dir, check=True)

    # Delete all file under dir1
    for file in os.listdir(os.path.join(source_files_dir, 'dir1')):
        os.remove(os.path.join(source_files_dir, 'dir1', file))

    subprocess.run(['borg', 'create', f'{repo_path}::test-archive5', source_files_dir], cwd=temp_dir, check=True)

    def cleanup():
        shutil.rmtree(temp_dir)

    atexit.register(cleanup)

    return repo_path, source_files_dir


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

    repo_path, source_dir = create_test_repo

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
            pass

        def open(self, func):
            func()

        def selectedFiles(self):
            return [str(tmpdir)]

    return MockFileDialog


@pytest.fixture
def borg_json_output():
    def _read_json(subcommand):
        stdout = open(f'tests/borg_json_output/{subcommand}_stdout.json')
        stderr = open(f'tests/borg_json_output/{subcommand}_stderr.json')
        return stdout, stderr

    return _read_json

@pytest.fixture
def rootdir():
    return os.path.dirname(os.path.abspath(__file__))
