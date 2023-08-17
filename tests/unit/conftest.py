import os
from datetime import datetime as dt

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
def init_db(qapp, qtbot, tmpdir_factory):
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

    new_repo = RepoModel(url='i0fi93@i593.repo.borgbase.com:repo')
    new_repo.encryption = 'none'
    new_repo.save()

    default_profile.repo = new_repo.id
    default_profile.dont_run_on_metered_networks = False
    default_profile.validation_on = False
    default_profile.save()

    test_archive = ArchiveModel(snapshot_id='99999', name='test-archive', time=dt(2000, 1, 1, 0, 0), repo=1)
    test_archive.save()

    test_archive1 = ArchiveModel(snapshot_id='99998', name='test-archive1', time=dt(2000, 1, 1, 0, 0), repo=1)
    test_archive1.save()

    source_dir = SourceFileModel(dir='/tmp/another', repo=new_repo, dir_size=100, dir_files_count=18, path_isdir=True)
    source_dir.save()

    qapp.main_window.deleteLater()
    del qapp.main_window
    qapp.main_window = MainWindow(qapp)  # Re-open main window to apply mock data in UI

    yield

    qapp.jobs_manager.cancel_all_jobs()
    qapp.backup_finished_event.disconnect()
    qapp.scheduler.schedule_changed.disconnect()
    qtbot.waitUntil(lambda: not qapp.jobs_manager.is_worker_running(), **pytest._wait_defaults)
    mock_db.close()


@pytest.fixture
def choose_file_dialog(*args):
    class MockFileDialog:
        def __init__(self, *args, **kwargs):
            pass

        def open(self, func):
            func()

        def selectedFiles(self):
            return ['/tmp']

    return MockFileDialog


@pytest.fixture
def borg_json_output():
    def _read_json(subcommand):
        stdout = open(f'tests/unit/borg_json_output/{subcommand}_stdout.json')
        stderr = open(f'tests/unit/borg_json_output/{subcommand}_stderr.json')
        return stdout, stderr

    return _read_json


@pytest.fixture
def rootdir():
    return os.path.dirname(os.path.abspath(__file__))


@pytest.fixture()
def archive_env(qapp, qtbot):
    """
    Common setup for unit tests involving the archive tab.
    """
    main: MainWindow = qapp.main_window
    tab: ArchiveTab = main.archiveTab
    main.tabWidget.setCurrentIndex(3)
    tab.populate_from_profile()
    qtbot.waitUntil(lambda: tab.archiveTable.rowCount() == 2, **pytest._wait_defaults)
    return main, tab
