import logging

import vorta.log


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


def test_no_log_file_when_disabled(monkeypatch, tmp_path):
    monkeypatch.setattr(vorta.log.config, 'LOG_DIR', tmp_path)
    monkeypatch.setattr(vorta.log, 'file_handler', None)
    logger = vorta.log.logger
    handlers, level = list(logger.handlers), logger.level
    other_levels = {name: logging.getLogger(name).level for name in ('peewee', 'PyQt6')}
    try:
        vorta.log.init_logger(background=True)
        vorta.log.set_file_logging(False)
        logger.info('not written to a file')
        assert not (tmp_path / 'vorta.log').exists()

        vorta.log.set_file_logging(True)
        logger.info('written to a file')
        assert (tmp_path / 'vorta.log').exists()
    finally:
        vorta.log.set_file_logging(False)
        logger.handlers = handlers
        logger.setLevel(level)
        for name, other_level in other_levels.items():
            logging.getLogger(name).setLevel(other_level)
