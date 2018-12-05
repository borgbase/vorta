from PyQt5.QtWidgets import QMenu, QSystemTrayIcon

from .borg.borg_thread import BorgThread
from .models import BackupProfileModel
from .utils import set_tray_icon


class TrayMenu(QSystemTrayIcon):
    def __init__(self, parent=None):
        QSystemTrayIcon.__init__(self, parent)
        self.app = parent
        set_tray_icon(self)
        menu = QMenu()

        # Workaround to get `activated` signal on Unity: https://stackoverflow.com/a/43683895/3983708
        menu.aboutToShow.connect(self.on_user_click)

        self.setContextMenu(menu)
        self.setVisible(True)
        self.show()

    def on_user_click(self):
        """Build system tray menu based on current state."""

        menu = self.contextMenu()
        menu.clear()

        status = menu.addAction(self.app.scheduler.next_job)
        status.setEnabled(False)

        if BorgThread.is_running():
            status.setText('Backup in Progress')
            cancel_action = menu.addAction("Cancel Backup")
            cancel_action.triggered.connect(self.app.backup_cancelled_event.emit)
        else:
            status.setText(f'Next Task: {self.app.scheduler.next_job}')
            profiles = BackupProfileModel.select()
            if profiles.count() > 1:
                profile_menu = menu.addMenu('Backup Now')
                for profile in profiles:
                    new_item = profile_menu.addAction(profile.name)
                    new_item.triggered.connect(lambda state, i=profile.id: self.app.create_backup_action(i))
            else:
                profile = profiles.first()
                profile_menu = menu.addAction('Backup Now')
                profile_menu.triggered.connect(lambda state, i=profile.id: self.app.create_backup_action(i))

        settings_action = menu.addAction("Settings")
        settings_action.triggered.connect(self.app.open_main_window_action)

        menu.addSeparator()

        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(self.app.quit)
