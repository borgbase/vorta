import os
from PyQt5 import uic
from PyQt5.QtCore import QProcess
from PyQt5.QtWidgets import QApplication

from paramiko.rsakey import RSAKey
from paramiko.ecdsakey import ECDSAKey
from paramiko.ed25519key import Ed25519Key

from ..utils import get_asset

uifile = get_asset('UI/sshadd.ui')
SSHAddUI, SSHAddBase = uic.loadUiType(uifile)

FORMAT_MAPPING = {
    'ed25519': Ed25519Key,
    'rsa': RSAKey,
    'ecdsa': ECDSAKey
}


class SSHAddWindow(SSHAddBase, SSHAddUI):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.closeButton.clicked.connect(self.accept)
        self.generateButton.clicked.connect(self.generate_key)

        self.init_format()
        self.init_length()

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

    def generate_key_result(self, exitCode, exitStatus):
        if exitCode == 0:
            output_path = os.path.expanduser(self.outputFileTextBox.text())
            pub_key = open(output_path + '.pub').read().strip()
            clipboard = QApplication.clipboard()
            clipboard.setText(pub_key)
            self.errors.setText(self.tr('New key was copied to clipboard and written to %s.') % output_path)
        else:
            self.errors.setText(self.tr('Error during key generation.'))

    def get_values(self):
        return {
            'ssh_key': self.sshComboBox.currentData(),
            'encryption': self.encryptionComboBox.currentData(),
            'repo_url': self.repoURL.text(),
            'password': self.passwordLineEdit.text()
        }
