"""
internationalisation (i18n) support code
"""
import logging
import os

from PyQt5.QtCore import QTranslator, QLocale

logger = logging.getLogger(__name__)


def init_translations(app):
    global application, translator, locale  # if we don't keep a reference on these, it stops working. pyqt bug?
    application = app
    translator = QTranslator()
    locale = QLocale()
    qm_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'qm'))
    ui_langs = locale.uiLanguages()
    succeeded = translator.load(locale, 'vorta', prefix='.', directory=qm_path)  # e.g. vorta/i18n/qm/vorta.de_DE.qm
    if succeeded:
        app.installTranslator(translator)
    logger.debug('Loading translation %s for %r.' % ('succeeded' if succeeded else 'failed', ui_langs))


def translate(*args, **kwargs):
    """
    small wrapper around QCoreApplication.translate()
    """
    global application  # see init_translation
    return application.translate(*args, **kwargs)


def trans_late(scope, text):
    """
    dummy translate function - only purpose is to mark scope/text for message extraction.

    later, at another place, there will be a translate(scope, text) call, with same
    scope and text, potentially not literal scope, not literal text, but from a variable.
    """
    return text
