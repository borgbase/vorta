import logging

import pytest
from peewee import SqliteDatabase

import vorta.log
from vorta.store.connection import file_logging_enabled
from vorta.store.models import SettingsModel


def test_set_file_logging(monkeypatch):
    handler = logging.NullHandler()
    monkeypatch.setattr(vorta.log, 'file_handler', handler)
    logger = vorta.log.logger
    try:
        vorta.log.set_file_logging(True)
        vorta.log.set_file_logging(True)
        assert logger.handlers.count(handler) == 1

        vorta.log.set_file_logging(False)
        assert handler not in logger.handlers
    finally:
        logger.removeHandler(handler)


def test_set_file_logging_before_init(monkeypatch):
    monkeypatch.setattr(vorta.log, 'file_handler', None)
    handlers = list(vorta.log.logger.handlers)

    vorta.log.set_file_logging(True)
    assert vorta.log.logger.handlers == handlers


@pytest.fixture
def log_dir(monkeypatch, tmp_path):
    """Lets a test call init_logger() with tmp_path as log dir, and undoes its changes to the root logger."""
    monkeypatch.setattr(vorta.log.config, 'LOG_DIR', tmp_path)
    for name in ('file_handler', 'console_handler', 'in_background'):
        monkeypatch.setattr(vorta.log, name, getattr(vorta.log, name))
    logger = vorta.log.logger
    handlers, level = list(logger.handlers), logger.level
    other_levels = {name: logging.getLogger(name).level for name in ('peewee', 'PyQt6')}
    yield tmp_path
    if vorta.log.file_handler is not None:
        vorta.log.file_handler.close()
    logger.handlers = handlers
    logger.setLevel(level)
    for name, other_level in other_levels.items():
        logging.getLogger(name).setLevel(other_level)


def test_no_log_file_when_disabled(log_dir):
    logger = vorta.log.logger
    vorta.log.init_logger(background=True, log_to_file=False)
    logger.info('not written to a file')
    assert not (log_dir / 'vorta.log').exists()

    vorta.log.set_file_logging(True)
    logger.info('written to a file')
    assert (log_dir / 'vorta.log').exists()


def test_console_logging_in_background(log_dir):
    """In background mode, logs go to the console while file logging is off, so they are not lost."""
    vorta.log.init_logger(background=True)
    assert vorta.log.file_handler in vorta.log.logger.handlers
    assert vorta.log.console_handler not in vorta.log.logger.handlers

    vorta.log.set_file_logging(False)
    assert vorta.log.file_handler not in vorta.log.logger.handlers
    assert vorta.log.console_handler in vorta.log.logger.handlers

    vorta.log.set_file_logging(True)
    assert vorta.log.file_handler in vorta.log.logger.handlers
    assert vorta.log.console_handler not in vorta.log.logger.handlers


def test_console_logging_in_foreground(log_dir):
    vorta.log.init_logger(background=False, log_to_file=False)
    assert vorta.log.file_handler not in vorta.log.logger.handlers
    assert vorta.log.console_handler in vorta.log.logger.handlers

    vorta.log.set_file_logging(True)
    assert vorta.log.file_handler in vorta.log.logger.handlers
    assert vorta.log.console_handler in vorta.log.logger.handlers


def test_file_logging_enabled(monkeypatch, tmp_path):
    """The setting is read from the database before init_db() runs."""
    monkeypatch.setattr(vorta.log, 'file_handler', None)  # saving the setting below calls set_file_logging()
    con = SqliteDatabase(str(tmp_path / 'settings.db'))
    assert file_logging_enabled(con)  # first start, no database file yet
    assert not (tmp_path / 'settings.db').exists()

    with con.connection_context():
        con.execute_sql('CREATE TABLE other (id INTEGER)')
    assert file_logging_enabled(con)  # no settings table yet

    with con.connection_context(), con.bind_ctx([SettingsModel]):
        con.create_tables([SettingsModel])
    assert file_logging_enabled(con)  # setting not saved yet

    with con.connection_context(), con.bind_ctx([SettingsModel]):
        setting = SettingsModel.create(key='enable_file_logging', value=True, label='', type='checkbox')
    assert file_logging_enabled(con)

    with con.connection_context(), con.bind_ctx([SettingsModel]):
        setting.value = False
        setting.save()
    assert not file_logging_enabled(con)
