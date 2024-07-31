from PyQt6 import uic

from vorta.store.models import BackupProfileMixin
from vorta.utils import (
    get_asset,
)
from vorta.views.archive_page import ArchivePage
from vorta.views.prune_options_page import PruneOptionsPage
from vorta.views.utils import get_colored_icon

uifile = get_asset('UI/archive_tab.ui')
ArchiveTabUI, ArchiveTabBase = uic.loadUiType(uifile)


class ArchiveTab(ArchiveTabBase, ArchiveTabUI, BackupProfileMixin):
    def __init__(self, parent=None, app=None):
        """Init."""
        super().__init__(parent)
        self.setupUi(parent)
        self.app = app
        self.toolBox.setCurrentIndex(0)
        self.init_archive_page(self.app)
        self.init_prune_options_page()
        self.app.paletteChanged.connect(lambda p: self.set_icons())
        self.set_icons()

    def init_archive_page(self, app=None):
        profile = self.profile()
        if profile.repo is not None:
            if profile.repo.name:
                repo_name = f"{profile.repo.name} ({profile.repo.url})"
            else:
                repo_name = profile.repo.url
            self.toolBox.setItemText(0, self.tr('Archives for {}').format(repo_name))
        self.archivePage = ArchivePage(self, app)
        self.archiveLayout.addWidget(self.archivePage)
        self.archivePage.show()

    def init_prune_options_page(self):
        self.pruneOptionsPage = PruneOptionsPage(self)
        self.pruneLayout.addWidget(self.pruneOptionsPage)
        self.pruneOptionsPage.show()

    def set_icons(self):
        """Used when changing between light- and dark mode"""
        self.toolBox.setItemIcon(0, get_colored_icon('tasks'))
        self.toolBox.setItemIcon(1, get_colored_icon('cut'))