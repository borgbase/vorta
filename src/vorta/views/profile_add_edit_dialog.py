from PyQt5 import uic
from ..utils import get_asset
from ..models import BackupProfileModel

uifile = get_asset('UI/profileadd.ui')
AddProfileUI, AddProfileBase = uic.loadUiType(uifile)


class AddProfileWindow(AddProfileBase, AddProfileUI):
    def __init__(self, parent=None, rename_existing_id=None):
        super().__init__(parent)
        self.setupUi(self)
        self.edited_profile = None

        self.buttonBox.rejected.connect(self.close)
        self.buttonBox.accepted.connect(self.save)

        if rename_existing_id is not None:
            existing_profile = BackupProfileModel.get(id=rename_existing_id)
            self.profileNameField.setText(existing_profile.name)
            self.existing_id = rename_existing_id
            self.modalTitle.setText('Rename Profile')

    def _set_status(self, text):
        self.errorText.setText(text)
        self.errorText.repaint()

    def save(self):
        if self.validate():
            new_profile = BackupProfileModel(name=self.profileNameField.text())
            new_profile.save()
            self.edited_profile = new_profile
            self.accept()

    def validate(self):
        name = self.profileNameField.text()
        # A name was entered?
        if len(name) == 0:
            self._set_status('Please enter a profile name.')
            return False

        # Profile with this name already exists?
        exists = BackupProfileModel.select().where(BackupProfileModel.name == name).count()
        if exists > 0:
            self._set_status('A profile with this name already exists.')
            return False

        return True


class EditProfileWindow(AddProfileWindow):
    def save(self):
        if self.validate():
            renamed_profile = BackupProfileModel.get(id=self.existing_id)
            renamed_profile.name = self.profileNameField.text()
            renamed_profile.save()
            self.edited_profile = renamed_profile
            self.accept()
