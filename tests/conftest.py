import pytest
import peewee
import sys
from datetime import datetime as dt

import vorta
from vorta.application import VortaApp
from vorta.models import RepoModel, SourceFileModel, ArchiveModel, BackupProfileModel


def pytest_configure(config):
    sys._called_from_test = True


@pytest.fixture
def app(tmpdir, qtbot):
    tmp_db = tmpdir.join('settings.sqlite')
    mock_db = peewee.SqliteDatabase(str(tmp_db))
    vorta.models.init_db(mock_db)

    new_repo = RepoModel(url='i0fi93@i593.repo.borgbase.com:repo')
    new_repo.save()

    profile = BackupProfileModel.get(id=1)
    profile.repo = new_repo.id
    profile.save()

    test_archive = ArchiveModel(snapshot_id='99999', name='test-archive', time=dt(2000, 1, 1, 0, 0), repo=1)
    test_archive.save()

    source_dir = SourceFileModel(dir='/tmp/another', repo=new_repo)
    source_dir.save()

    app = VortaApp([])
    app.open_main_window_action()
    qtbot.addWidget(app.main_window)
    return app


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
