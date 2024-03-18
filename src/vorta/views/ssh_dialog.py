import os

from PyQt6 import QtCore, uic
from PyQt6.QtCore import QProcess, Qt, pyqtSlot
from PyQt6.QtWidgets import QApplication, QDialogButtonBox

from ..utils import get_asset

uifile = get_asset('UI/sshadd.ui')
SSHAddUI, SSHAddBase = uic.loadUiType(uifile)


class SSHAddWindow(SSHAddBase, SSHAddUI):
    failure = QtCore.pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # dialogButtonBox
        self.generateButton = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)

        self.generateButton.setText(self.tr("Generate and copy to clipboard"))

        # signals
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.accepted.connect(self.generate_key)

        self.init_format()
        self.init_length()

    def retranslateUi(self, dialog):
        """Retranslate strings in ui."""
        super().retranslateUi(dialog)

        # setupUi calls retranslateUi
        if hasattr(self, 'generateButton'):
            self.generateButton.setText(self.tr("Generate and copy to clipboard"))

    def init_format(self):
        self.formatSelect.addItem(self.tr('ED25519 (Recommended)'), 'ed25519')
        self.formatSelect.addItem(self.tr('RSA (Legacy)'), 'rsa')
        self.formatSelect.addItem(self.tr('ECDSA'), 'ecdsa')
        self.outputFileTextBox.setText('~/.ssh/id_ed25519')
        self.formatSelect.currentIndexChanged.connect(self.format_select_change)

    def format_select_change(self, index):
        new_output = f'~/.ssh/id_{self.formatSelect.currentData()}'
        self.outputFileTextBox.setText(new_output)

    def init_length(self):
        self.lengthSelect.addItem(self.tr('High (Recommended)'), ('4096', '521'))
        self.lengthSelect.addItem(self.tr('Medium'), ('2048', '384'))

    def generate_key(self):
        format = self.formatSelect.currentData()
        length = self.lengthSelect.currentData()

        if format == 'rsa':
            length = length[0]
        else:
            length = length[1]

        output_path = os.path.expanduser(self.outputFileTextBox.text())
        if os.path.isfile(output_path):
            self.errors.setText(self.tr('Key file already exists. Not overwriting.'))
        else:
            self.sshproc = QProcess(self)
            self.sshproc.finished.connect(self.generate_key_result)
            self.sshproc.start('ssh-keygen', ['-t', format, '-b', length, '-f', output_path, '-N', ''])

    @pyqtSlot(int)
    def generate_key_result(self, exit_code):
        if exit_code == 0:
            output_path = os.path.expanduser(self.outputFileTextBox.text())
            pub_key = open(output_path + '.pub').read().strip()
            clipboard = QApplication.clipboard()
            clipboard.setText(pub_key)
            self.reject()
        else:
            self.reject()
            self.failure.emit(exit_code)

    def get_values(self):
        return {
            'ssh_key': self.sshComboBox.currentData(),
            'encryption': self.encryptionComboBox.currentData(),
            'repo_url': self.repoURL.text(),
            'password': self.passwordLineEdit.text(),
        }
