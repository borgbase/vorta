import logging

from PyQt6 import QtCore, uic

from vorta import config
from vorta._version import __version__
from vorta.store.models import BackupProfileMixin
from vorta.utils import get_asset

uifile = get_asset('UI/abouttab.ui')
AboutTabUI, AboutTabBase = uic.loadUiType(uifile)

logger = logging.getLogger(__name__)


class AboutTab(AboutTabBase, AboutTabUI, BackupProfileMixin):
    refresh_archive = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        """Init."""
        super().__init__(parent)
        self.setupUi(parent)
        self.versionLabel.setText(__version__)
        self.logLink.setText(
            f'<a href="file://{config.LOG_DIR}"><span style="text-decoration:'
            'underline; color:#0984e3;">Click here</span></a> to see the logs.'
        )

    def set_borg_details(self, version, path):
        self.borgVersion.setText(version)
        self.borgPath.setText(f"Borg path: {path}")
