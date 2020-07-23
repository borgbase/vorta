import re
from PyQt5 import uic

from vorta.utils import get_private_keys, get_asset, choose_file_dialog, \
    borg_compat
from vorta.borg.init import BorgInitThread
from vorta.borg.info import BorgInfoThread
from vorta.i18n import translate
from vorta.views.utils import get_colored_icon, validate_passwords, password_transparency
from vorta.models import RepoModel

uifile = get_asset('UI/repoadd.ui')
AddRepoUI, AddRepoBase = uic.loadUiType(uifile)


class AddRepoWindow(AddRepoBase, AddRepoUI):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.result = None
        self.is_remote_repo = True

        self.closeButton.clicked.connect(self.close)
        self.saveButton.clicked.connect(self.run)
        self.chooseLocalFolderButton.clicked.connect(self.choose_local_backup_folder)
        self.useRemoteRepoButton.clicked.connect(self.use_remote_repo_action)
        self.passwordLineEdit.textChanged.connect(self.password_listener)
        self.confirmLineEdit.textChanged.connect(self.password_listener)
        self.encryptionComboBox.activated.connect(self.password_transparency)
        self.tabWidget.setCurrentIndex(0)

        self.init_encryption()
        self.init_ssh_key()
        self.set_icons()
        self.password_transparency()

    def set_icons(self):
        self.chooseLocalFolderButton.setIcon(get_colored_icon('folder-open'))
        self.useRemoteRepoButton.setIcon(get_colored_icon('globe'))

    @property
    def values(self):
        out = dict(
            ssh_key=self.sshComboBox.currentData(),
            repo_url=self.repoURL.text(),
            password=self.passwordLineEdit.text(),
            extra_borg_arguments=self.extraBorgArgumentsLineEdit.text()
        )
        if self.__class__ == AddRepoWindow:
            out['encryption'] = self.encryptionComboBox.currentData()
        return out

    def password_transparency(self):
        self.passwordLabel.setText(password_transparency(self.values.get('encryption')))

    def choose_local_backup_folder(self):
        def receive():
            folder = dialog.selectedFiles()
            if folder:
                self.repoURL.setText(folder[0])
                self.repoURL.setEnabled(False)
                self.sshComboBox.setEnabled(False)
                self.repoLabel.setText(self.tr('Repository Path:'))
                self.is_remote_repo = False

        dialog = choose_file_dialog(self, self.tr("Choose Location of Borg Repository"))
        dialog.open(receive)

    def use_remote_repo_action(self):
        self.repoURL.setText('')
        self.repoURL.setEnabled(True)
        self.sshComboBox.setEnabled(True)
        self.extraBorgArgumentsLineEdit.setText('')
        self.repoLabel.setText(self.tr('Repository URL:'))
        self.is_remote_repo = True

    def run(self):
        if self.validate() and self.password_listener():
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
        else:
            self._set_status(self.tr('Unable to add your repository.'))

    def init_encryption(self):
        encryption_algos = [
            ['Repokey-Blake2 (Recommended, key stored in repository)', 'repokey-blake2'],
            ['Repokey', 'repokey'],
            ['Keyfile-Blake2 (Key stored in home directory)', 'keyfile-blake2'],
            ['Keyfile', 'keyfile'],
            ['None (not recommended)', 'none']
        ]

        for desc, name in encryption_algos:
            self.encryptionComboBox.addItem(self.tr(desc), name)

        if not borg_compat.check('BLAKE2'):
            self.encryptionComboBox.model().item(0).setEnabled(False)
            self.encryptionComboBox.model().item(2).setEnabled(False)
            self.encryptionComboBox.setCurrentIndex(1)

    def init_ssh_key(self):
        keys = get_private_keys()
        for key in keys:
            self.sshComboBox.addItem(f'{key["filename"]} ({key["format"]}:{key["fingerprint"]})', key['filename'])

    def validate(self):
        """Pre-flight check for valid input and borg binary."""
        if self.is_remote_repo and not re.match(r'.+:.+', self.values['repo_url']):
            self._set_status(self.tr('Please enter a valid repo URL or select a local path.'))
            return False

        if RepoModel.get_or_none(RepoModel.url == self.values['repo_url']) is not None:
            self._set_status(self.tr('This repo has already been added.'))
            return False

        return True

    def password_listener(self):
        if self.values['encryption'] == 'none':
            self.passwordLabel.setText("")
            return True
        else:
            firstPass = self.passwordLineEdit.text()
            secondPass = self.confirmLineEdit.text()
            msg = validate_passwords(firstPass, secondPass)
            self.passwordLabel.setText(translate('utils', msg))
            return len(msg) == 0


class ExistingRepoWindow(AddRepoWindow):
    def __init__(self):
        super().__init__()
        self.encryptionComboBox.hide()
        self.encryptionLabel.hide()
        self.title.setText(self.tr('Connect to existing Repository'))
        self.passwordLineEdit.textChanged.disconnect()
        self.confirmLineEdit.textChanged.disconnect()
        self.confirmLineEdit.hide()
        self.confirmLabel.hide()

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
