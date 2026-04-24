from PyQt6 import QtCore
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QTabWidget, QVBoxLayout


class SettingsDialog(QDialog):
    def __init__(self, parent=None, misc_tab=None, about_tab=None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Settings"))
        self.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
        self.setWindowFlag(QtCore.Qt.WindowType.WindowContextHelpButtonHint, False)
        self.resize(820, 620)

        layout = QVBoxLayout(self)

        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs)

        if misc_tab is not None:
            misc_tab.setParent(self.tabs)
            self.tabs.addTab(misc_tab, self.tr("Settings"))

        if about_tab is not None:
            about_tab.setParent(self.tabs)
            self.tabs.addTab(about_tab, self.tr("About"))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.reject)
        layout.addWidget(buttons)

    def open_settings(self):
        self.setWindowTitle(self.tr("Settings"))
        self.tabs.setCurrentIndex(0)

    def open_about(self):
        self.setWindowTitle(self.tr("About"))
        self.tabs.setCurrentIndex(1)