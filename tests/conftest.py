import os
import peewee
import pytest
import sys
from datetime import datetime as dt
from pathlib import Path
from shutil import copyfile
from unittest.mock import MagicMock

import vorta
from vorta.models import (RepoModel, RepoPassword, BackupProfileModel, SourceFileModel,
                          SettingsModel, ArchiveModel, WifiSettingModel, EventLogModel, SchemaVersion)
from vorta.views.main_window import MainWindow

models = [RepoModel, RepoPassword, BackupProfileModel, SourceFileModel,
          SettingsModel, ArchiveModel, WifiSettingModel, EventLogModel, SchemaVersion]


def pytest_configure(config):
    sys._called_from_test = True
    pytest._wait_defaults = {'timeout': 20000}
    os.environ['LANG'] = 'en'  # Ensure we test an English UI


@pytest.fixture(scope='session')
def qapp(tmpdir_factory):
    # DB is required to init QApplication. New DB used for every test.
    tmp_db = tmpdir_factory.mktemp('Vorta').join('settings.sqlite')
    mock_db = peewee.SqliteDatabase(str(tmp_db))
    vorta.models.init_db(mock_db)

    from vorta.application import VortaApp
    VortaApp.set_borg_details_action = MagicMock()  # Can't use pytest-mock in session scope
    VortaApp.scheduler = MagicMock()

    qapp = VortaApp([])  # Only init QApplication once to avoid segfaults while testing.

    yield qapp
    mock_db.close()
    qapp.quit()


@pytest.fixture(scope='function', autouse=True)
def init_db(request, qapp, qtbot, tmpdir_factory):
    tmp_db = tmpdir_factory.mktemp('Vorta').join('settings.sqlite')
    mock_db = peewee.SqliteDatabase(str(tmp_db), pragmas={'journal_mode': 'wal', })
    vorta.models.init_db(mock_db)

    # the bootstrap profile file can be set via @pytest.mark.profile_bootstrap_file('/some/path.json')
    # using this pytest mark skips the creation of default data
    profile_bootstrap_file_marker = request.node.get_closest_marker('profile_bootstrap_file')
    if profile_bootstrap_file_marker:
        # copy the file because it is consumed by the main window
        original_bootstrap_file = profile_bootstrap_file_marker.args[0]
        bootstrap_copy = Path(tmpdir_factory.mktemp('Vorta').join('profile.json'))
        copyfile(original_bootstrap_file, bootstrap_copy)
        profile_bootstrap_file = bootstrap_copy
    else:
        # point the bootstrap file to a non-existing file to prevent accidental import during tests
        profile_bootstrap_file = Path(tmpdir_factory.mktemp('Vorta').join('does_not_exist.json'))

        default_profile = BackupProfileModel(name='Default')
        default_profile.save()

        new_repo = RepoModel(url='i0fi93@i593.repo.borgbase.com:repo')
        new_repo.encryption = 'none'
        new_repo.save()

        default_profile.repo = new_repo.id
        default_profile.dont_run_on_metered_networks = False
        default_profile.save()

        test_archive = ArchiveModel(snapshot_id='99999', name='test-archive', time=dt(2000, 1, 1, 0, 0), repo=1)
        test_archive.save()

        test_archive1 = ArchiveModel(snapshot_id='99998', name='test-archive1', time=dt(2000, 1, 1, 0, 0), repo=1)
        test_archive1.save()

        source_dir = SourceFileModel(dir='/tmp/another', repo=new_repo, dir_size=100, dir_files_count=18,
                                     path_isdir=True)
        source_dir.save()

    qapp.main_window.deleteLater()
    del qapp.main_window
    # Re-open main window to apply mock data in UI
    qapp.main_window = MainWindow(qapp, profile_bootstrap_file=profile_bootstrap_file)

    yield
    qapp.backup_cancelled_event.emit()
    qtbot.waitUntil(lambda: not vorta.borg.borg_thread.BorgThread.is_running())
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
        stdout = open(f'tests/borg_json_output/{subcommand}_stdout.json')
        stderr = open(f'tests/borg_json_output/{subcommand}_stderr.json')
        return stdout, stderr
    return _read_json


@pytest.fixture
def rootdir():
    return os.path.dirname(os.path.abspath(__file__))
