
import pytest
import peewee

import vorta
from vorta.application import VortaApp

@pytest.fixture()
def app(tmpdir):
    tmp_db = tmpdir.join('settings.sqlite')
    mock_db = peewee.SqliteDatabase(str(tmp_db))
    vorta.models.init_db(mock_db)
    return VortaApp([])
