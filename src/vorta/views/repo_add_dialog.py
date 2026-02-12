import re

from PyQt6 import QtCore, uic
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QSizePolicy,
)

from vorta.borg.info_repo import BorgInfoRepoJob
from vorta.borg.init import BorgInitJob
from vorta.keyring.abc import VortaKeyring
from vorta.store.models import RepoModel
from vorta.utils import borg_compat, choose_file_dialog, get_asset, get_private_keys
from vorta.views.partials.password_input import PasswordInput, PasswordLineEdit
from vorta.views.utils import get_colored_icon

uifile = get_asset('UI/repo_add.ui')
AddRepoUI, AddRepoBase = uic.loadUiType(uifile)


class RepoWindow(AddRepoBase, AddRepoUI):
    added_repo = QtCore.pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        self.result = None
        self.is_remote_repo = True

        self.setMinimumWidth(583)

        self.saveButton = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        self.saveButton.setText(self.tr("Add"))

        self.buttonBox.rejected.connect(self.close)
        self.buttonBox.accepted.connect(self.run)
        self.chooseLocalFolderButton.clicked.connect(self.choose_local_backup_folder)
        self.useRemoteRepoButton.clicked.connect(self.use_remote_repo_action)
        self.repoURL.textChanged.connect(self.set_password)

        self.tabWidget.setCurrentIndex(0)

        self.init_ssh_key()
        self.set_icons()

    def retranslateUi(self, dialog):
        """Retranslate strings in ui."""
        super().retranslateUi(dialog)

        # setupUi calls retranslateUi
        if hasattr(self, 'saveButton'):
            self.saveButton.setText(self.tr("Add"))

    def set_icons(self):
        self.chooseLocalFolderButton.setIcon(get_colored_icon('folder-open'))
        self.useRemoteRepoButton.setIcon(get_colored_icon('globe'))

    def choose_local_backup_folder(self):
        def receive():
            folder = dialog.selectedFiles()
            if folder:
                self.repoURL.setText(folder[0])
                self.repoName.setText(folder[0].split('/')[-1])
                self.repoURL.setEnabled(False)
                self.sshComboBox.setEnabled(False)
                self.repoLabel.setText(self.tr('Repository Path:'))
                self.is_remote_repo = False

        dialog = choose_file_dialog(self, self.tr("Choose Location of Borg Repository"))
        dialog.open(receive)

    def use_remote_repo_action(self):
        self.repoURL.setText('')
        self.repoURL.setEnabled(True)
        self.repoName.setText('')
        self.sshComboBox.setEnabled(True)
        self.extraBorgArgumentsLineEdit.setText('')
        self.repoLabel.setText(self.tr('Repository URL:'))
        self.is_remote_repo = True

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
    
    def prompt_key_backup(self, repo):
        """
        Prompt user to backup their repository key after creation.
        This is called by AddRepoWindow after successful repository initialization.
        """
        pass  # To be overridden in AddRepoWindow

    def init_ssh_key(self):
        keys = get_private_keys()
        for key in keys:
            self.sshComboBox.addItem(f'{key}', key)

    def validate(self):
        """Pre-flight check for valid input and borg binary."""
        if self.is_remote_repo and not re.match(r'.+:.+', self.values['repo_url']):
            self._set_status(self.tr('Please enter a valid repo URL or select a local path.'))
            return False

        if len(self.values['repo_name']) > 64:
            self._set_status(self.tr('Repository name must be less than 65 characters.'))
            return False

        if RepoModel.get_or_none(RepoModel.url == self.values['repo_url']) is not None:
            self._set_status(self.tr('This repo has already been added.'))
            return False

        return True

    @property
    def values(self):
        out = dict(
            ssh_key=self.sshComboBox.currentData(),
            repo_url=self.repoURL.text(),
            repo_name=self.repoName.text(),
            password=self.passwordInput.get_password(),
            extra_borg_arguments=self.extraBorgArgumentsLineEdit.text(),
        )
        return out


class AddRepoWindow(RepoWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Repository")

        self.passwordInput = PasswordInput()
        self.passwordInput.add_form_to_layout(self.repoDataFormLayout)

        self.encryptionLabel = QLabel(self.tr('Encryption:'))
        self.encryptionComboBox = QComboBox()
        self.encryptionComboBox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.advancedFormLayout.setWidget(1, QFormLayout.ItemRole.LabelRole, self.encryptionLabel)
        self.advancedFormLayout.setWidget(1, QFormLayout.ItemRole.FieldRole, self.encryptionComboBox)

        self.encryptionComboBox.activated.connect(self.display_backend_warning)
        self.encryptionComboBox.currentIndexChanged.connect(self.encryption_listener)

        self.display_backend_warning()
        self.init_encryption()

    def set_password(self, URL):
        '''Autofill password from keyring only if current entry is empty'''
        password = VortaKeyring.get_keyring().get_password('vorta-repo', URL)
        if password and self.passwordInput.get_password() == "":
            self.passwordInput.set_error_label(self.tr("Autofilled password from password manager."))
            self.passwordInput.passwordLineEdit.setText(password)
            self.passwordInput.confirmLineEdit.setText(password)

    @property
    def values(self):
        out = super().values
        out['encryption'] = self.encryptionComboBox.currentData()
        return out

    def init_encryption(self):
        if borg_compat.check('V2'):
            encryption_algos = [
                [
                    self.tr('Repokey-ChaCha20-Poly1305 (Recommended, key stored in repository)'),
                    'repokey-blake2-chacha20-poly1305',
                ],
                [
                    self.tr('Keyfile-ChaCha20-Poly1305 (Key stored in home directory)'),
                    'keyfile-blake2-chacha20-poly1305',
                ],
                [self.tr('Repokey-AES256-OCB'), 'repokey-blake2-aes-ocb'],
                [self.tr('Keyfile-AES256-OCB'), 'keyfile-blake2-aes-ocb'],
                [self.tr('None (not recommended)'), 'none'],
            ]
        else:
            encryption_algos = [
                [self.tr('Repokey-Blake2 (Recommended, key stored in repository)'), 'repokey-blake2'],
                [self.tr('Repokey'), 'repokey'],
                [self.tr('Keyfile-Blake2 (Key stored in home directory)'), 'keyfile-blake2'],
                [self.tr('Keyfile'), 'keyfile'],
                [self.tr('None (not recommended)'), 'none'],
            ]

        for desc, name in encryption_algos:
            self.encryptionComboBox.addItem(desc, name)

        if not borg_compat.check('BLAKE2'):
            self.encryptionComboBox.model().item(0).setEnabled(False)
            self.encryptionComboBox.model().item(2).setEnabled(False)
            self.encryptionComboBox.setCurrentIndex(1)

    def encryption_listener(self):
        '''Validates passwords only if its going to be used'''
        if self.values['encryption'] == 'none':
            self.passwordInput.set_validation_enabled(False)
            self.passwordInput.set_visibility(False)
        else:
            self.passwordInput.set_validation_enabled(True)
            self.passwordInput.set_visibility(True)

    def display_backend_warning(self):
        '''Display password backend message based off current keyring'''
        if self.encryptionComboBox.currentData() != 'none':
            self.passwordInput.set_error_label(VortaKeyring.get_keyring().get_backend_warning())

    def validate(self):
        return super().validate() and self.passwordInput.validate()

    def run_result(self, result):
        """Handle result of repository initialization."""
        self.saveButton.setEnabled(True)
        if result['returncode'] == 0:
            # Check if repository is encrypted
            encryption = result['params'].get('encryption', 'none')
            if encryption != 'none':
                # Prompt user to backup their key
                self.prompt_key_backup(result)
            else:
                # No encryption, just emit and close
                self.added_repo.emit(result)
                self.accept()
        else:
            self._set_status(self.tr('Unable to add your repository.'))
    
    def prompt_key_backup(self, result):
        """Show prompt to backup repository key after successful creation."""
        # Extract any warning messages from Borg output
        warning_text = ""
        if 'data' in result:
            # Check for key-related messages in Borg output
            for line in result.get('data', []):
                if isinstance(line, dict):
                    message = line.get('message', '')
                    if any(keyword in message.lower() for keyword in ['key', 'safe', 'inaccessible']):
                        warning_text += message + "\n"
        
        msg = QMessageBox(self)
        msg.setWindowTitle(self.tr("Repository Created Successfully"))
        msg.setIcon(QMessageBox.Icon.Information)
        
        # Build message text
        message = self.tr("Your encrypted repository has been created.\n\n"
                         "It is strongly recommended to backup your encryption key now. "
                         "Without this key, you will not be able to access your backups "
                         "if your local key is lost or corrupted.")
        
        # Add Borg's warnings if any
        if warning_text:
            message += "\n\n" + self.tr("Borg message:") + "\n" + warning_text.strip()
        
        msg.setText(message)
        msg.setInformativeText(self.tr("Would you like to export your key now?"))
        
        export_button = msg.addButton(self.tr("Export Key Now"), QMessageBox.ButtonRole.AcceptRole)
        later_button = msg.addButton(self.tr("Skip"), QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(export_button)
        
        msg.exec()
        
        if msg.clickedButton() == export_button:
            # User wants to export the key
            # We need to emit the result first so the repo is added to the UI
            self.added_repo.emit(result)
            # Close this dialog
            self.accept()
            # Trigger key export from the main window
            # We'll use QTimer to delay this slightly to ensure UI is ready
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, self._trigger_key_export)
        else:
            # User skipped, just add repo and close
            self.added_repo.emit(result)
            self.accept()
    
    def _trigger_key_export(self):
        """Trigger the key export action on the main window."""
        # Get the main window's repo tab and trigger export
        main_window = QApplication.instance().main_window
        if main_window and hasattr(main_window, 'repoTab'):
            main_window.repoTab.repo_export_key_action()

    def run(self):
        if self.validate():
            params = BorgInitJob.prepare(self.values)
            if params['ok']:
                self.saveButton.setEnabled(False)
                job = BorgInitJob(params['cmd'], params)
                job.updated.connect(self._set_status)
                job.result.connect(self.run_result)
                QApplication.instance().jobs_manager.add_job(job)
            else:
                self._set_status(params['message'])


class ExistingRepoWindow(RepoWindow):
    def __init__(self):
        super().__init__()
        self.title.setText(self.tr('Connect to existing Repository'))
        self.setWindowTitle("Add Existing Repository")

        self.passwordLabel = QLabel(self.tr('Password:'))
        self.passwordInput = PasswordLineEdit(placeholder_text=self.tr("Enter the encryption passphrase"))
        self.repoDataFormLayout.addRow(self.passwordLabel, self.passwordInput)

    def set_password(self, URL):
        '''Autofill password from keyring only if current entry is empty'''
        password = VortaKeyring.get_keyring().get_password('vorta-repo', URL)
        if password and self.passwordInput.get_password() == "":
            self._set_status(self.tr("Autofilled password from password manager."))
            self.passwordInput.setText(password)

    def run(self):
        if self.validate():
            params = BorgInfoRepoJob.prepare(self.values)
            if params['ok']:
                self.saveButton.setEnabled(False)
                job = BorgInfoRepoJob(params['cmd'], params)
                job.updated.connect(self._set_status)
                job.result.connect(self.run_result)
                self.thread = job  # Keep reference for tests
                QApplication.instance().jobs_manager.add_job(job)
            else:
                self._set_status(params['message'])
