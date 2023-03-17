from unittest import TestCase, mock
from vorta.application import VortaApp


class TestApplication(TestCase):
    def setUp(self):
        self.app = VortaApp([])

    @mock.patch('vorta.store.models.SettingsModel.get')
    @mock.patch('vorta.application.QMessageBox')
    @mock.patch('pathlib.Path.exists')
    @mock.patch('os.access')
    def test_check_darwin_permissions_with_full_access_enabled(
        self, mock_access, mock_exists, mock_msgbox, mock_settings
    ):
        mock_settings.return_value.value = True
        mock_exists.return_value = True
        mock_access.return_value = False

        self.app.check_darwin_permissions()

        # Assert that the correct methods were called on the mock objects
        mock_settings.assert_called_with(key='check_full_disk_access')
        mock_exists.assert_called_with()
        mock_access.assert_called_with(mock.ANY, mock.ANY)
        mock_msgbox.return_value.setIcon.assert_called_with(mock.ANY)
        mock_msgbox.return_value.setTextInteractionFlags.assert_called_with(mock.ANY)
        mock_msgbox.return_value.setText.assert_called_with(mock.ANY)
        mock_msgbox.return_value.setInformativeText.assert_called_with(mock.ANY)
        mock_msgbox.return_value.setStandardButtons.assert_called_with(mock.ANY)
        mock_msgbox.return_value.exec.assert_called_with()

    @mock.patch('vorta.store.models.SettingsModel.get')
    @mock.patch('vorta.application.logger')
    def test_check_darwin_permissions_with_full_access_disabled(self, mock_logger, mock_settings):
        mock_settings.return_value.value = False

        self.app.check_darwin_permissions()

        # Assert that the correct methods were called on the mock objects
        mock_settings.assert_called_with(key='check_full_disk_access')
        mock_logger.info.assert_called_with('Skipping check due to setting')

    def tearDown(self):
        self.app = None
