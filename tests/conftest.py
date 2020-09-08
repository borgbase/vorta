import pytest
import peewee
import sys
import os
from datetime import datetime as dt
from unittest.mock import MagicMock

import vorta
from vorta.models import (RepoModel, RepoPassword, BackupProfileModel, SourceFileModel,
                          SettingsModel, ArchiveModel, WifiSettingModel, EventLogModel, SchemaVersion)


models = [RepoModel, RepoPassword, BackupProfileModel, SourceFileModel,
          SettingsModel, ArchiveModel, WifiSettingModel, EventLogModel, SchemaVersion]


def pytest_configure(config):
    sys._called_from_test = True


@pytest.fixture(scope='function', autouse=True)
def init_db(qapp):
    vorta.models.db.drop_tables(models)
    vorta.models.init_db()

    new_repo = RepoModel(url='i0fi93@i593.repo.borgbase.com:repo')
    new_repo.save()

    profile = BackupProfileModel.get(id=1)
    profile.repo = new_repo.id
    profile.dont_run_on_metered_networks = False
    profile.save()

    test_archive = ArchiveModel(snapshot_id='99999', name='test-archive', time=dt(2000, 1, 1, 0, 0), repo=1)
    test_archive.save()

    test_archive1 = ArchiveModel(snapshot_id='99998', name='test-archive1', time=dt(2000, 1, 1, 0, 0), repo=1)
    test_archive1.save()

    source_dir = SourceFileModel(dir='/tmp/another', repo=new_repo)
    source_dir.save()

    qapp.open_main_window_action()


@pytest.fixture(scope='session', autouse=True)
def local_en():
    """
    Some tests use English strings. So override whatever language the current user
    has and run the tests with the English UI.
    """
    os.environ['LANG'] = 'en'


@pytest.fixture(scope='session')
def qapp(tmpdir_factory, local_en):
    tmp_db = tmpdir_factory.mktemp('Vorta').join('settings.sqlite')
    mock_db = peewee.SqliteDatabase(str(tmp_db))
    vorta.models.init_db(mock_db)

    from vorta.application import VortaApp
    VortaApp.set_borg_details_action = MagicMock()  # Can't use pytest-mock in session scope
    VortaApp.scheduler = MagicMock()

    qapp = VortaApp([])  # Only init QApplication once to avoid segfaults while testing.

    yield qapp


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
