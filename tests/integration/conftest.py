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

    file_path = os.path.join(source_files_dir, 'file')
    with open(file_path, 'w') as f:
        f.write('test')

    subprocess.run(['borg', 'create', f'{repo_path}::test-archive', source_files_dir], cwd=temp_dir, check=True)

    dir_path = os.path.join(source_files_dir, 'dir')
    os.mkdir(dir_path)

    file_path = os.path.join(dir_path, 'file')
    with open(file_path, 'w') as f:
        f.write('test')

    subprocess.run(['borg', 'create', f'{repo_path}::test-archive1', source_files_dir], cwd=temp_dir, check=True)

    symlink_path = os.path.join(source_files_dir, 'symlink')
    os.symlink(file_path, symlink_path)

    subprocess.run(['borg', 'create', f'{repo_path}::test-archive2', source_files_dir], cwd=temp_dir, check=True)

    # TODO: More file types and more archives required for testing

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
