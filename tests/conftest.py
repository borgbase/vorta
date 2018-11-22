import io
import pytest
import peewee

import vorta
from vorta.application import VortaApp
from vorta.models import RepoModel, SourceDirModel


@pytest.fixture()
def app(tmpdir, qtbot):
    tmp_db = tmpdir.join('settings.sqlite')
    mock_db = peewee.SqliteDatabase(str(tmp_db))
    vorta.models.init_db(mock_db)
    app = VortaApp([])
    qtbot.addWidget(app.main_window)
    return app


@pytest.fixture()
def app_with_repo(app):
    profile = app.main_window.current_profile
    new_repo = RepoModel(url='i0fi93@i593.repo.borgbase.com:repo')
    new_repo.save()
    profile.repo = new_repo
    profile.save()

    source_dir = SourceDirModel(dir='/tmp', repo=new_repo)
    source_dir.save()
    return app


@pytest.fixture
def borg_json_output():
    def _read_json(subcommand):
        stdout = open(f'tests/borg_json_output/{subcommand}_stdout.json').read()
        stderr = open(f'tests/borg_json_output/{subcommand}_stderr.json').read()
        return io.StringIO(stdout), io.StringIO(stderr)
    return _read_json
