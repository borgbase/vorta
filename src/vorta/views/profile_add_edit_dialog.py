from PyQt6 import QtCore, uic
from PyQt6.QtWidgets import QDialogButtonBox

from vorta.i18n import trans_late, translate
from vorta.store.models import BackupProfileModel
from vorta.utils import get_asset

uifile = get_asset('UI/profileadd.ui')
AddProfileUI, AddProfileBase = uic.loadUiType(uifile)


class AddProfileWindow(AddProfileBase, AddProfileUI):
    profile_changed = QtCore.pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        self.edited_profile = None

        self.buttonBox.rejected.connect(self.close)
        self.buttonBox.accepted.connect(self.save)
        self.profileNameField.textChanged.connect(self.button_validation)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Save).setText(self.tr("Save"))
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText(self.tr("Cancel"))

        self.name_blank = trans_late('AddProfileWindow', 'Please enter a profile name.')
        self.name_exists = trans_late('AddProfileWindow', 'A profile with this name already exists.')
        # Call validate to set inital messages
        self.buttonBox.button(QDialogButtonBox.StandardButton.Save).setEnabled(self.validate())

    def _set_status(self, text):
        self.errorText.setText(text)
        self.errorText.repaint()

    def save(self):
        new_profile = BackupProfileModel(name=self.profileNameField.text())
        new_profile.save()
        self.profile_changed.emit(new_profile.name, new_profile.id)
        self.accept()

    def button_validation(self):
        self.buttonBox.button(QDialogButtonBox.StandardButton.Save).setEnabled(self.validate())

    def validate(self):
        name = self.profileNameField.text()
        # A name was entered?
        if len(name) == 0:
            self._set_status(translate('AddProfileWindow', self.name_blank))
            return False

        # Profile with this name already exists?
        exists = BackupProfileModel.select().where(BackupProfileModel.name == name).count()
        if exists > 0:
            self._set_status(translate('AddProfileWindow', self.name_exists))
            return False

        self._set_status('')
        return True


class EditProfileWindow(AddProfileWindow):
    def __init__(self, parent=None, rename_existing_id=None):
        super().__init__(parent)
        existing_profile = BackupProfileModel.get(id=rename_existing_id)
        self.profileNameField.setText(existing_profile.name)
        self.existing_id = rename_existing_id
        self.modalTitle.setText(self.tr('Rename Profile'))

    def save(self):
        renamed_profile = BackupProfileModel.get(id=self.existing_id)
        renamed_profile.name = self.profileNameField.text()
        renamed_profile.save()
        self.profile_changed.emit(renamed_profile.name, renamed_profile.id)
        self.accept()
