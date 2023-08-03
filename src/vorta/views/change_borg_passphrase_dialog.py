from PyQt6 import QtCore, uic
from PyQt6.QtWidgets import QApplication, QDialogButtonBox

from vorta.borg.change_passphrase import BorgChangePassJob
from vorta.utils import get_asset
from vorta.views.partials.password_input import PasswordInput

uifile = get_asset('UI/changeborgpass.ui')
ChangeBorgPassUI, ChangeBorgPassBase = uic.loadUiType(uifile)


class ChangeBorgPassphraseWindow(ChangeBorgPassBase, ChangeBorgPassUI):
    change_borg_passphrase = QtCore.pyqtSignal(dict)

    def __init__(self, profile):
        super().__init__()
        self.setupUi(self)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        self.result = None
        self.profile = profile

        self.setMinimumWidth(583)

        self.passwordInput = PasswordInput()
        self.passwordInput.add_form_to_layout(self.repoDataFormLayout)

        self.saveButton = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        self.saveButton.setText(self.tr("Update"))

        self.buttonBox.rejected.connect(self.close)
        self.buttonBox.accepted.connect(self.run)

    def retranslateUi(self, dialog):
        """Retranslate strings in ui."""
        super().retranslateUi(dialog)

        # setupUi calls retranslateUi
        if hasattr(self, 'saveButton'):
            self.saveButton.setText(self.tr("Update"))

    def run(self):
        # if self.password_listener() and self.validate():
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
            self._set_status(self.tr('Unable to change Borg passphrase.'))

    # def validate(self):
    #     """Check encryption type"""
    #     if self.profile.repo.encryption.startswith('repokey'):
    #         return True
    #     self.errorText.setText(translate('utils', 'Encryption type must be repokey.'))
    #     return False
