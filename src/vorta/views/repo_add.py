from PyQt5 import uic
from ..utils import get_private_keys, get_asset, choose_folder_dialog
from vorta.borg.init import BorgInitThread
from vorta.borg.info import BorgInfoThread
from vorta.borg.list import BorgListThread

uifile = get_asset('UI/repoadd.ui')
AddRepoUI, AddRepoBase = uic.loadUiType(uifile, from_imports=True, import_from='vorta.views')


class AddRepoWindow(AddRepoBase, AddRepoUI):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.result = None

        self.closeButton.clicked.connect(self.close)
        self.saveButton.clicked.connect(self.run)
        self.chooseLocalFolderButton.clicked.connect(self.choose_local_backup_folder)
        self.useRemoteRepoButton.clicked.connect(self.use_remote_repo_action)

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

    def choose_local_backup_folder(self):
        folder = choose_folder_dialog(self, "Choose Location of Borg Repository")
        if folder:
            self.repoURL.setText(folder)
            self.repoURL.setEnabled(False)
            self.sshComboBox.setEnabled(False)
            self.repoLabel.setText('Repository Path:')

    def use_remote_repo_action(self):
        self.repoURL.setText('')
        self.repoURL.setEnabled(True)
        self.sshComboBox.setEnabled(True)
        self.repoLabel.setText('Repository URL:')

    def run(self):
        if self.validate():
            params = BorgInitThread.prepare(self.values)
            if params['ok']:
                self.saveButton.setEnabled(False)
                thread = BorgInitThread(params['cmd'], params, parent=self)
                thread.updated.connect(self._set_status)
                thread.result.connect(self.run_result)
                self.thread = thread  # Needs to be connected to self for tests to work.
                self.thread.start()
            else:
                self._set_status(params['message'])

    def _set_status(self, text):
        self.errorText.setText(text)
        self.errorText.repaint()

    def run_result(self, result):
        self.saveButton.setEnabled(True)
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
        """Pre-flight check for valid input and borg binary."""
        if len(self.values['repo_url']) < 5:
            self._set_status('Please enter a valid repo URL or path.')
            return False

        if self.__class__ == AddRepoWindow:
            if self.values['encryption'] != 'none':
                if len(self.values['password']) < 8:
                    self._set_status('Please use a longer password.')
                    return False

        return True


class ExistingRepoWindow(AddRepoWindow):
    def __init__(self):
        super().__init__()
        self.encryptionComboBox.hide()
        self.encryptionLabel.hide()
        self.title.setText('Connect to existing Repository')

    def run(self):
        if self.validate():
            params = BorgInfoThread.prepare(self.values)
            if params['ok']:
                self.saveButton.setEnabled(False)
                thread = BorgInfoThread(params['cmd'], params, parent=self)
                thread.updated.connect(self._set_status)
                thread.result.connect(self.run_result)
                self.thread = thread  # Needs to be connected to self for tests to work.
                self.thread.start()
            else:
                self._set_status(params['message'])
