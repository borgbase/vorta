import os
from PyQt5.QtWidgets import QMenu, QSystemTrayIcon
from PyQt5.QtGui import QIcon

from vorta.store.models import BackupProfileModel
from vorta.utils import get_asset


class TrayMenu(QSystemTrayIcon):
    def __init__(self, parent=None):
        QSystemTrayIcon.__init__(self, parent)
        self.app = parent
        self.set_tray_icon()
        menu = QMenu()

        # Workaround to get `activated` signal on Unity: https://stackoverflow.com/a/43683895/3983708
        menu.aboutToShow.connect(self.on_user_click)

        self.setContextMenu(menu)

        self.activated.connect(self.on_activation)
        self.setVisible(True)
        self.show()

    def on_activation(self, reason):
        """
        XDG-compliant tray behavior: right click to open a context menu, and left click to
        restore the application.

        If XDG_CURRENT_DESKTOP isn't set, always open the tray menu (macOS)
        """
        if reason in [QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick] and \
                os.environ.get('XDG_CURRENT_DESKTOP'):
            self.app.toggle_main_window_visibility()

    def on_user_click(self):
        """Build system tray menu based on current state."""

        menu = self.contextMenu()
        menu.clear()

        open_action = menu.addAction(self.tr('Vorta for Borg Backup'))
        open_action.triggered.connect(self.app.open_main_window_action)

        menu.addSeparator()

        next_task_time = self.app.scheduler.next_job()
        status = menu.addAction(next_task_time)
        status.setEnabled(False)

        if self.app.jobs_manager.is_worker_running():
            status.setText(self.tr('Task in progress'))
            cancel_action = menu.addAction(self.tr('Cancel Backup'))
            cancel_action.triggered.connect(self.app.backup_cancelled_event.emit)
        else:
            status.setText(self.tr('Next Task: %s') % next_task_time)
            profiles = BackupProfileModel.select()
            if profiles.count() > 1:
                profile_menu = menu.addMenu(self.tr('Backup Now'))
                for profile in profiles:
                    new_item = profile_menu.addAction(profile.name)
                    new_item.triggered.connect(lambda state, i=profile.id: self.app.create_backup_action(i))
            else:
                profile = profiles.first()
                profile_menu = menu.addAction(self.tr('Backup Now'))
                profile_menu.triggered.connect(lambda state, i=profile.id: self.app.create_backup_action(i))

        menu.addSeparator()

        exit_action = menu.addAction(self.tr('Quit'))
        exit_action.triggered.connect(self.app.quit)

    def set_tray_icon(self, active=False):
        """
        Use white tray icon, when on Gnome or in dark mode. Otherwise use dark icon.
        """
        icon_name = f"icons/hdd-o{'-active' if active else ''}.png"
        icon = QIcon(get_asset(icon_name))
        self.setIcon(icon)
