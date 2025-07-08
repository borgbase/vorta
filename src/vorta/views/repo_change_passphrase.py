from PyQt6 import QtCore, uic
from PyQt6.QtWidgets import QApplication, QDialogButtonBox, QLabel

from vorta.borg.change_passphrase import BorgChangePassJob
from vorta.keyring.abc import VortaKeyring
from vorta.utils import get_asset
from vorta.views.partials.password_input import PasswordInput

uifile = get_asset('UI/change_passphrase.ui')
ChangeBorgPassUI, ChangeBorgPassBase = uic.loadUiType(uifile)


class ChangeBorgPassphraseWindow(ChangeBorgPassBase, ChangeBorgPassUI):
    change_borg_passphrase = QtCore.pyqtSignal(dict)

    def __init__(self, profile):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle(self.tr("Change Passphrase"))
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        self.result = None
        self.profile = profile

        self.setMinimumWidth(583)

        self.passwordInput = PasswordInput()

        self.repoDataFormLayout.addRow("", self.title)  # Add title inside the form
        self.repoDataFormLayout.addRow(QLabel(self.tr("Repository:")), QLabel(str(self.profile.repo.url)))
        self.passwordInput.add_form_to_layout(self.repoDataFormLayout)

        self.saveButton = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        self.saveButton.setText(self.tr("Update"))

        self.buttonBox.rejected.connect(self.close)
        self.buttonBox.accepted.connect(self.run)

    def run(self):
        if self.passwordInput.validate():
            newPass = self.passwordInput.passwordLineEdit.text()

            params = BorgChangePassJob.prepare(self.profile, newPass)
            if params['ok']:
                self.saveButton.setEnabled(False)
                job = BorgChangePassJob(params['cmd'], params)
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
            self.change_borg_passphrase.emit(result)
            self.accept()
        else:
            self._set_status(self.tr('Unable to change the borg passphrase.'))
