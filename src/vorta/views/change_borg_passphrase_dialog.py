from PyQt5 import QtCore, uic
from PyQt5.QtWidgets import QAction, QApplication, QDialogButtonBox, QLineEdit
from vorta.borg.change_passphrase import BorgChangePassJob
from vorta.i18n import translate
from vorta.utils import get_asset, validate_passwords
from vorta.views.utils import get_colored_icon

uifile = get_asset('UI/changeborgpass.ui')
ChangeBorgPassUI, ChangeBorgPassBase = uic.loadUiType(uifile)


class ChangeBorgPassphraseWindow(ChangeBorgPassBase, ChangeBorgPassUI):
    change_borg_passphrase = QtCore.pyqtSignal(dict)

    def __init__(self, profile):
        super().__init__()
        self.setupUi(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.result = None
        self.profile = profile

        # dialogButtonBox
        self.saveButton = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        self.saveButton.setText(self.tr("Update"))

        self.buttonBox.rejected.connect(self.close)
        self.buttonBox.accepted.connect(self.run)
        self.passwordLineEdit.textChanged.connect(self.password_listener)
        self.confirmLineEdit.textChanged.connect(self.password_listener)

        # Add clickable icon to toggle password visibility to end of box
        self.showHideAction = QAction(self.tr("Show my passwords"), self)
        self.showHideAction.setCheckable(True)
        self.showHideAction.toggled.connect(self.set_visibility)

        self.passwordLineEdit.addAction(self.showHideAction, QLineEdit.TrailingPosition)

        self.set_icons()

    def retranslateUi(self, dialog):
        """Retranslate strings in ui."""
        super().retranslateUi(dialog)

        # setupUi calls retranslateUi
        if hasattr(self, 'saveButton'):
            self.saveButton.setText(self.tr("Update"))

    def set_icons(self):
        self.showHideAction.setIcon(get_colored_icon("eye"))

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

    def run(self):
        # if self.password_listener() and self.validate():
        if self.password_listener():
            oldPass = self.oldPasswordLineEdit.text()
            newPass = self.passwordLineEdit.text()

            params = BorgChangePassJob.prepare(self.profile, oldPass, newPass)
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

    def validate(self):
        """Check encryption type"""
        if self.profile.repo.encryption in ['repokey', 'repokey-blake2']:
            return True
        self.errorText.setText(translate('utils', 'Encryption type must be repokey.'))
        return False

    def password_listener(self):
        '''Validates passwords only if its going to be used'''
        oldPass = self.oldPasswordLineEdit.text()
        firstPass = self.passwordLineEdit.text()
        secondPass = self.confirmLineEdit.text()

        # Since borg originally does not have minimum character requirement
        if len(oldPass) < 1:
            self.errorText.setText(translate('utils', 'Old password is required.'))
            return False

        msg = validate_passwords(firstPass, secondPass)
        self.errorText.setText(translate('utils', msg))
        return not bool(msg)
