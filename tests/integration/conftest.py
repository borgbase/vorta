import os
import subprocess
import time

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


@pytest.fixture(scope='function', autouse=True)
def create_test_repo(tmpdir_factory):
    repo_path = tmpdir_factory.mktemp('repo')
    source_files_dir = tmpdir_factory.mktemp('borg_src')

    subprocess.run(['borg', 'init', '--encryption=none', str(repo_path)], check=True)

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
    subprocess.run(['borg', 'create', f'{repo_path}::test-archive1', source_files_dir], cwd=str(repo_path), check=True)
    # Sleep 1 second to prevent timestamp issue where both archives have the same timestamp causing issue with diff
    time.sleep(1)

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

    subprocess.run(['borg', 'create', f'{repo_path}::test-archive2', source_files_dir], cwd=str(repo_path), check=True)
    time.sleep(1)

    # Rename dir to dir1
    os.rename(dir_path, os.path.join(source_files_dir, 'dir1'))

    subprocess.run(['borg', 'create', f'{repo_path}::test-archive3', source_files_dir], cwd=str(repo_path), check=True)
    time.sleep(1)

    # Rename all files under dir1
    for file in os.listdir(os.path.join(source_files_dir, 'dir1')):
        os.rename(os.path.join(source_files_dir, 'dir1', file), os.path.join(source_files_dir, 'dir1', file + '1'))

    subprocess.run(['borg', 'create', f'{repo_path}::test-archive4', source_files_dir], cwd=str(repo_path), check=True)
    time.sleep(1)

    # Delete all file under dir1
    for file in os.listdir(os.path.join(source_files_dir, 'dir1')):
        os.remove(os.path.join(source_files_dir, 'dir1', file))

    subprocess.run(['borg', 'create', f'{repo_path}::test-archive5', source_files_dir], cwd=str(repo_path), check=True)
    time.sleep(1)

    # change permission of dir1
    os.chmod(os.path.join(source_files_dir, 'dir1'), 0o700)

    subprocess.run(['borg', 'create', f'{repo_path}::test-archive6', source_files_dir], cwd=str(repo_path), check=True)
    time.sleep(1)

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
