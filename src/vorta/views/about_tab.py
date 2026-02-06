import logging
from datetime import datetime

from PyQt6 import QtCore, uic

from vorta import config
from vorta._version import __version__
from vorta.i18n import trans_late, translate
from vorta.i18n.richtext import escape, format_richtext, link
from vorta.store.models import BackupProfileMixin
from vorta.utils import get_asset
from vorta.views.utils import get_colored_icon

uifile = get_asset('UI/about_tab.ui')
AboutTabUI, AboutTabBase = uic.loadUiType(uifile)

logger = logging.getLogger(__name__)


class AboutTab(AboutTabBase, AboutTabUI, BackupProfileMixin):
    refresh_archive = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        """Init."""
        super().__init__(parent)
        self.setupUi(parent)
        self.versionLabel.setText(__version__)
        self.bug_report_text = trans_late('Form', '%1 to report a bug.')
        self.docs_text = trans_late('Form', '%1 to view the docs.')
        self.repo_text = trans_late('Form', '%1 to view Git repo.')
        self.click_here = trans_late('Form', 'Click here')
        self.view_logs_text = trans_late('Form', 'View the logs')
        self._set_links()
        self.gpl_logo.setPixmap(get_colored_icon('gpl_logo', scaled_height=40, return_qpixmap=True))
        self.python_logo.setPixmap(get_colored_icon('python_logo', scaled_height=40, return_qpixmap=True))
        copyright_text = self.copyrightLabel.text()
        copyright_text = copyright_text.replace('2020', str(datetime.now().year))
        self.copyrightLabel.setText(copyright_text)

    def _set_links(self):
        click_here = translate('Form', self.click_here)

        bug_template = self.bugReportLink.text()
        bug_sentence = format_richtext(
            escape(translate('Form', self.bug_report_text)),
            link('https://github.com/borgbase/vorta/issues/new/choose', click_here),
        )
        self.bugReportLink.setText(format_richtext(bug_template, bug_sentence))

        docs_template = self.docsLink.text()
        docs_sentence = format_richtext(
            escape(translate('Form', self.docs_text)),
            link('https://borgbackup.readthedocs.io/en/master/index.html', click_here),
        )
        self.docsLink.setText(format_richtext(docs_template, docs_sentence))

        repo_template = self.repoLink.text()
        repo_sentence = format_richtext(
            escape(translate('Form', self.repo_text)),
            link('https://github.com/borgbase/vorta', click_here),
        )
        self.repoLink.setText(format_richtext(repo_template, repo_sentence))

        log_template = self.logLink.text()
        log_link = link(f"file://{config.LOG_DIR}", translate('Form', self.view_logs_text))
        self.logLink.setText(format_richtext(log_template, log_link))

    def set_borg_details(self, version, path):
        self.borgVersion.setText(version)
        self.borgPath.setText(f"<center>Path to Borg: {path}</center>")
