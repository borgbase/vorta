import re
from PyQt5 import uic, QtCore
from PyQt5.QtWidgets import QLineEdit, QAction, QApplication

from vorta.utils import get_private_keys, get_asset, choose_file_dialog, \
    borg_compat, validate_passwords
from vorta.keyring.abc import VortaKeyring
from vorta.borg.init import BorgInitJob
from vorta.borg.info_repo import BorgInfoRepoJob
from vorta.i18n import translate
from vorta.views.utils import get_colored_icon
from vorta.store.models import RepoModel

uifile = get_asset('UI/repoadd.ui')
AddRepoUI, AddRepoBase = uic.loadUiType(uifile)


class AddRepoWindow(AddRepoBase, AddRepoUI):
    added_repo = QtCore.pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.result = None
        self.is_remote_repo = True

        self.closeButton.clicked.connect(self.close)
        self.saveButton.clicked.connect(self.run)
        self.chooseLocalFolderButton.clicked.connect(self.choose_local_backup_folder)
        self.useRemoteRepoButton.clicked.connect(self.use_remote_repo_action)
        self.repoURL.textChanged.connect(self.set_password)
        self.passwordLineEdit.textChanged.connect(self.password_listener)
        self.confirmLineEdit.textChanged.connect(self.password_listener)
        self.encryptionComboBox.activated.connect(self.display_backend_warning)

        # Add clickable icon to toggle password visibility to end of box
        self.showHideAction = QAction(self.tr("Show my passwords"), self)
        self.showHideAction.setCheckable(True)
        self.showHideAction.toggled.connect(self.set_visibility)

        self.passwordLineEdit.addAction(self.showHideAction, QLineEdit.TrailingPosition)

        self.tabWidget.setCurrentIndex(0)

        self.init_encryption()
        self.init_ssh_key()
        self.set_icons()
        self.display_backend_warning()

    def set_icons(self):
        self.chooseLocalFolderButton.setIcon(get_colored_icon('folder-open'))
        self.useRemoteRepoButton.setIcon(get_colored_icon('globe'))
        self.showHideAction.setIcon(get_colored_icon("eye"))

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

    def display_backend_warning(self):
        '''Display password backend message based off current keyring'''
        if self.encryptionComboBox.currentData() != 'none':
            self.passwordLabel.setText(VortaKeyring.get_keyring().get_backend_warning())

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

    def set_password(self, URL):
        ''' Autofill password from keyring only if current entry is empty '''
        password = VortaKeyring.get_keyring().get_password('vorta-repo', URL)
        if password and self.passwordLineEdit.text() == "":
            self.passwordLabel.setText(self.tr("Autofilled password from password manager."))
            self.passwordLineEdit.setText(password)
            if self.__class__ == AddRepoWindow:
                self.confirmLineEdit.setText(password)

    def set_visibility(self, visible):
        visibility = QLineEdit.Normal if visible else QLineEdit.Password
        self.passwordLineEdit.setEchoMode(visibility)
        self.confirmLineEdit.setEchoMode(visibility)

        if visible:
            self.showHideAction.setIcon(get_colored_icon("eye-slash"))
            self.showHideAction.setText(self.tr("Hide my passwords"))
        else:
            self.showHideAction.setIcon(get_colored_icon("eye"))
            self.showHideAction.setText(self.tr("Show my passwords"))

    def use_remote_repo_action(self):
        self.repoURL.setText('')
        self.repoURL.setEnabled(True)
        self.sshComboBox.setEnabled(True)
        self.extraBorgArgumentsLineEdit.setText('')
        self.repoLabel.setText(self.tr('Repository URL:'))
        self.is_remote_repo = True

    # No need to add this function to JobsManager because repo is set for the first time
    def run(self):
        if self.validate() and self.password_listener():
            params = BorgInitJob.prepare(self.values)
            if params['ok']:
                self.saveButton.setEnabled(False)
                job = BorgInitJob(params['cmd'], params)
                job.updated.connect(self._set_status)
                job.result.connect(self.run_result)
                QApplication.instance().jobs_manager.add_job(job)
            else:
                self._set_status(params['message'])

    def _set_status(self, text):
        self.errorText.setText(text)
        self.errorText.repaint()

    def run_result(self, result):
        self.saveButton.setEnabled(True)
        if result['returncode'] == 0:
            self.added_repo.emit(result)
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
        ''' Validates passwords only if its going to be used '''
        if self.values['encryption'] == 'none':
            self.passwordLabel.setText("")
            return True
        else:
            firstPass = self.passwordLineEdit.text()
            secondPass = self.confirmLineEdit.text()
            msg = validate_passwords(firstPass, secondPass)
            self.passwordLabel.setText(translate('utils', msg))
            return not bool(msg)


class ExistingRepoWindow(AddRepoWindow):
    def __init__(self):
        super().__init__()
        self.encryptionComboBox.hide()
        self.encryptionLabel.hide()
        self.title.setText(self.tr('Connect to existing Repository'))
        self.showHideAction.setText(self.tr("Show my password"))
        self.passwordLineEdit.textChanged.disconnect()
        self.confirmLineEdit.textChanged.disconnect()
        self.confirmLineEdit.hide()
        self.confirmLabel.hide()
        del self.confirmLineEdit
        del self.confirmLabel

    def set_visibility(self, visible):
        visibility = QLineEdit.Normal if visible else QLineEdit.Password
        self.passwordLineEdit.setEchoMode(visibility)

        if visible:
            self.showHideAction.setIcon(get_colored_icon("eye-slash"))
            self.showHideAction.setText(self.tr("Hide my password"))
        else:
            self.showHideAction.setIcon(get_colored_icon("eye"))
            self.showHideAction.setText(self.tr("Show my password"))

    def run(self):
        if self.validate():
            params = BorgInfoRepoJob.prepare(self.values)
            if params['ok']:
                self.saveButton.setEnabled(False)
                thread = BorgInfoRepoJob(params['cmd'], params)
                thread.updated.connect(self._set_status)
                thread.result.connect(self.run_result)
                self.thread = thread  # Needs to be connected to self for tests to work.
                self.thread.run()
            else:
                self._set_status(params['message'])
