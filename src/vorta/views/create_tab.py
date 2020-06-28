from PyQt5 import uic
from ..utils import get_asset
from vorta.models import RepoModel, BackupProfileMixin

uifile = get_asset('UI/createtab.ui')
CreateTabUI, CreateTabBase = uic.loadUiType(uifile)

class CreateTab(CreateTabUI, CreateTabBase, BackupProfileMixin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(parent)

        self.saveButton.clicked.connect(self.testValues)

    @property
    def values(self):
        self.buttonMapping = {
            '--dry-run': self.dryRun,
            '--no-cache-sync': self.cacheSync,
            '--exclude-caches': self.cacheTag,
            '--no-files-cache': self.filesCache,
            '--keep-exclude-tags': self.exclusionTags,
            '--one-file-system': self.oneFS,
            '--numeric-owner': self.numericOwner,
            '--noatime': self.noatime,
            '--noctime': self.noctime,
            '--nobirthtime': self.nobirthtime,
            '--nobsdflags': self.nobsdflags,
            '--ignore-inode': self.ignoreInode,
            '--numeric-owner': self.numericOwner,
            '--read-special': self.readSpecial
        }
        list = ['--checkpoint-interval', f'{self.checkpointInterval.value()}']
        for label, obj in self.buttonMapping.items():
            if obj.isChecked():
                list.append(label)

        return list

    def testValues(self):
        print(self.values)
        
