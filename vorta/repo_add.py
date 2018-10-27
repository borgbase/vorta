import os
from PyQt5 import uic
from .utils import get_private_keys

uifile = os.path.join(os.path.dirname(__file__), 'UI/repoadd.ui')
AddRepoUI, AddRepoBase = uic.loadUiType(uifile)


class AddRepoWindow(AddRepoBase, AddRepoUI):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.closeButton.clicked.connect(self.close)
        self.saveButton.clicked.connect(self.validate)

        self.init_encryption()
        self.init_ssh_key()

    def init_encryption(self):
        self.encryptionComboBox.model().item(0).setEnabled(False)
        self.encryptionComboBox.addItem('Repokey-Blake2 (Recommended)', 'repokey-blake2')
        self.encryptionComboBox.addItem('Repokey', 'repokey')
        self.encryptionComboBox.addItem('None (not recommended', 'none')

    def init_ssh_key(self):
        keys = get_private_keys()
        for key in keys:
            self.sshComboBox.addItem(f'{key["filename"]} ({key["format"]}:{key["fingerprint"]})', key['filename'])

    def validate(self):
        if len(self.repoURL.text()) < 5:
            self.errorText.setText('Please enter a repo URL.')
            return

        if self.encryptionComboBox.isVisible() and self.encryptionComboBox.currentData() is None:
            self.errorText.setText('Please choose an encryption mode.')
            return

        self.accept()

    def get_values(self):
        return {
            'ssh_key': self.sshComboBox.currentData(),
            'encryption': self.encryptionComboBox.currentData(),
            'repo_url': self.repoURL.text(),
            'password': self.passwordLineEdit.text()
        }


class ExistingRepoWindow(AddRepoWindow):
    def __init__(self):
        super().__init__()
        self.encryptionComboBox.hide()
        self.encryptionLabel.hide()

    def get_values(self):
        return {
            'ssh_key': self.sshComboBox.currentData(),
            'repo_url': self.repoURL.text(),
            'password': self.passwordLineEdit.text()
        }
