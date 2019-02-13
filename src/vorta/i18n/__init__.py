"""
internationalisation (i18n) support code
"""
import logging
import os

from PyQt5.QtCore import QTranslator, QLocale

logger = logging.getLogger(__name__)

# To check if the UI layout copes flexibly with translated strings, an env var
# TRANS_SCALE can be used - it will result in transformed translated strings, e.g.:
# 100 = scale 100%, normal
# N>0 = scale to N%
# N<0 = additionally, do a RTL simulation at scale -N%
# usage: TRANS_SCALE=200 LANG=de_DE vorta --foreground
trans_scale = int(os.environ.get('TRANS_SCALE', '100'))


class VortaTranslator(QTranslator):
    """
    Extends QTranslator to increase the length of strings for testing. Fallback for untranslated
    strings to English doesn't work currently. So only use for testing.
    """
    def translate(self, context, text, disambiguation=None, n=-1):
        translated = super().translate(context, text, disambiguation=disambiguation, n=n)
        scale = trans_scale

        # for UI layout debugging:
        has_placeholders = '%' in translated
        has_html = translated.startswith('<') and translated.endswith('>')
        if has_placeholders or has_html:
            # not supported kinds of strings, just return normal:
            return translated
        if scale < 0:
            # for simple RTL checking: reverse translated string
            translated = translated[::-1]
            scale = -scale
        if 0 < scale < 100:
            step = 100 // scale
            scale = None
        else:
            step = None
            scale = scale // 100
        return translated * scale if step is None else translated[::step]


def init_translations(app):
    """
    Loads translations for a given input app. If a scaling factor is defined for testing, we use
    our own subclass of QTranslator.
    """
    global application, translator, locale  # if we don't keep a reference on these, it stops working. pyqt bug?
    application = app
    translator = QTranslator() if trans_scale == 100 else VortaTranslator()

    locale = QLocale(os.environ.get('LANG', None))
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
