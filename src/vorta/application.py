import sys
from PyQt5.QtWidgets import QApplication

from .tray_menu import TrayMenu
from .scheduler import VortaScheduler
from .models import BackupProfileModel
from .borg_runner import BorgThread
from .views.main_window import MainWindow


class VortaApp(QApplication):
    def __init__(self, args):
        super().__init__(args)
        self.thread = None
        self.setQuitOnLastWindowClosed(False)
        self.scheduler = VortaScheduler(self)

        # Prepare tray and connect events.
        self.tray = TrayMenu(self)
        self.tray.start_backup.connect(self.create_backup)
        self.tray.open_main_window.connect(self.on_open_main_window)

        # Prepare main window
        self.main_window = MainWindow(self)

        if not getattr(sys, 'frozen', False):
            self.main_window.show()

    @property
    def profile(self):
        return BackupProfileModel.get(id=1)

    def cancel_backup(self):
        if self.thread and self.thread.isRunning():
            self.thread.process.kill()
            self.thread.terminate()

    def create_backup(self):
        if self.thread and self.thread.isRunning():
            print('backup already in progress')
        else:
            msg = BorgThread.prepare_runner()
            if msg['ok']:
                self.thread = BorgThread(msg['cmd'], msg['params'])
                self.thread.updated.connect(self.create_backup_log)
                self.thread.result.connect(self.create_backup_result)
                self.thread.start()

    def on_open_main_window(self):
        self.main_window.show()

    def create_backup_log(self, text):
        print(text)

    def create_backup_result(self, result):
        self.createStartBtn.setEnabled(True)
        self.createStartBtn.repaint()
        self.set_status(progress_max=100)
        if result['returncode'] == 0:
            new_snapshot, created = SnapshotModel.get_or_create(
                snapshot_id=result['data']['archive']['id'],
                defaults={
                    'name': result['data']['archive']['name'],
                    'time': parser.parse(result['data']['archive']['start']),
                    'repo': self.profile.repo
                }
            )
            new_snapshot.save()
            if 'cache' in result['data'] and created:
                stats = result['data']['cache']['stats']
                repo = self.profile.repo
                repo.total_size = stats['total_size']
                repo.unique_csize = stats['unique_csize']
                repo.unique_size = stats['unique_size']
                repo.total_unique_chunks = stats['total_unique_chunks']
                repo.save()
            self.snapshotTab.populate()

