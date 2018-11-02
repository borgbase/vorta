from PyQt5 import uic, QtCore
from ..utils import get_private_keys, get_asset
from ..borg_thread import BorgThread

uifile = get_asset('UI/repoadd.ui')
AddRepoUI, AddRepoBase = uic.loadUiType(uifile)


class AddRepoWindow(AddRepoBase, AddRepoUI):
    connection_message = 'Setting up new repo...'
    cmd = ["borg", "init", "--log-json"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.result = None

        self.closeButton.clicked.connect(self.close)
        self.saveButton.clicked.connect(self.run)

        self.init_encryption()
        self.init_ssh_key()

    @property
    def values(self):
        out = dict(
            ssh_key=self.sshComboBox.currentData(),
            repo_url=self.repoURL.text(),
            password=self.passwordLineEdit.text()
        )
        if self.__class__ == AddRepoWindow:
            out['encryption'] = self.encryptionComboBox.currentData()
        return out

    def run(self):
        if self.validate():
            self.set_status(self.connection_message)
            cmd = self.cmd + [self.values['repo_url']]
            thread = BorgThread(cmd, self.values, parent=self)
            thread.updated.connect(self.set_status)
            thread.result.connect(self.run_result)
            self.thread = thread
            self.thread.start()

    def set_status(self, text):
        self.errorText.setText(text)
        self.errorText.repaint()

    def run_result(self, result):
        if result['returncode'] == 0:
            self.result = result
            self.accept()

    def init_encryption(self):
        self.encryptionComboBox.addItem('Repokey-Blake2 (Recommended, key stored remotely)', 'repokey-blake2')
        self.encryptionComboBox.addItem('Repokey', 'repokey')
        self.encryptionComboBox.addItem('Keyfile-Blake2 (Key stored locally)', 'keyfile-blake2')
        self.encryptionComboBox.addItem('Keyfile', 'keyfile')
        self.encryptionComboBox.addItem('None (not recommended', 'none')

    def init_ssh_key(self):
        keys = get_private_keys()
        for key in keys:
            self.sshComboBox.addItem(f'{key["filename"]} ({key["format"]}:{key["fingerprint"]})', key['filename'])

    def validate(self):
        if len(self.values['repo_url']) < 5 or ':' not in self.values['repo_url']:
            self.set_status('Please enter a valid repo URL including hostname and path.')
            return False

        if self.__class__ == AddRepoWindow:
            if self.values['encryption'] != 'none' and len(self.values['password']) < 8:
                self.set_status('Please use a longer password.')
                return False

            self.cmd.append(f"--encryption={self.values['encryption']}")

        return True


class ExistingRepoWindow(AddRepoWindow):
    connection_message = 'Validating existing repo...'
    cmd = ["borg", "list", "--json"]

    def __init__(self):
        super().__init__()
        self.encryptionComboBox.hide()
        self.encryptionLabel.hide()
        self.title.setText('Connect to existing Repository')
