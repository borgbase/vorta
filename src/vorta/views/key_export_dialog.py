from PyQt6 import QtCore, uic

from vorta.utils import get_asset

uifile = get_asset('UI/key_export_dialog.ui')
KeyExportDialogUI, KeyExportDialogBase = uic.loadUiType(uifile)


class KeyExportDialog(KeyExportDialogBase, KeyExportDialogUI):
    """Dialog for selecting the format to export a repository key."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        # Note: Not using WA_DeleteOnClose since we need to query dialog state after exec()

    def get_format_flags(self):
        """Return the command-line flags for the selected format."""
        if self.qrHtmlRadio.isChecked():
            return ['--qr-html']
        elif self.paperRadio.isChecked():
            return ['--paper']
        else:
            # Plain text (default) - no flags needed
            return []

    def get_default_extension(self):
        """Return the default file extension for the selected format."""
        if self.qrHtmlRadio.isChecked():
            return '.html'
        else:
            # Both plain text and paper format use .txt
            return '.txt'
