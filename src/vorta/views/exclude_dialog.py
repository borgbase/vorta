from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QStandardItem, QStandardItemModel

from vorta.utils import get_asset

uifile = get_asset('UI/excludedialog.ui')
ExcludeDialogUi, ExcludeDialogBase = uic.loadUiType(uifile)


class ExcludeDialog(ExcludeDialogBase, ExcludeDialogUi):
    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.profile = profile
        self.setWindowTitle(self.tr('Add patterns to exclude'))

        self.sample_exclusion_data = [
            {'pattern': '*/.DS_Store', 'enabled': True, 'comment': 'Mac OS X Finder metadata file'},
            {'pattern': '*/.TemporaryItems', 'enabled': False, 'comment': 'Mac OS X temporary files'},
            {
                'pattern': '*/.Spotlight-V100',
                'enabled': True,
                'comment': None,
            },
            {
                'pattern': '*/.Trashes',
                'enabled': False,
                'comment': None,
            },
        ]
        self.poupulate_excludes()

    def poupulate_excludes(self):
        model = QStandardItemModel()
        self.customExclusionsList.setModel(model)

        for exclude in self.sample_exclusion_data:
            item = QStandardItem(exclude['pattern'])
            item.setCheckable(True)
            item.setCheckState(Qt.CheckState.Checked if exclude['enabled'] else Qt.CheckState.Unchecked)

            if exclude['comment']:
                item.setToolTip(exclude['comment'])

            model.appendRow(item)
