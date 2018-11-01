from datetime import timedelta
from PyQt5 import uic
from PyQt5.QtWidgets import QFileDialog, QTableWidgetItem, QTableView, QHeaderView

from ..borg_runner import BorgThread
from ..utils import get_asset, keyring, pretty_bytes
from ..models import BackupProfileMixin

uifile = get_asset('UI/snapshottab.ui')
SnapshotUI, SnapshotBase = uic.loadUiType(uifile)


class SnapshotTab(SnapshotBase, SnapshotUI, BackupProfileMixin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(parent)

        header = self.snapshotTable.horizontalHeader()
        header.setVisible(True)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        self.snapshotTable.setSelectionBehavior(QTableView.SelectRows)
        self.snapshotTable.setEditTriggers(QTableView.NoEditTriggers)

        self.snapshotMountButton.clicked.connect(self.snapshot_mount)
        self.snapshotDeleteButton.clicked.connect(self.snapshot_mount)
        self.snapshotRefreshButton.clicked.connect(self.snapshot_mount)

        self.populate()

    def set_status(self, text):
        self.mountErrors.setText(text)
        self.mountErrors.repaint()

    def populate(self):
        if self.profile.repo:
            snapshots = [s for s in self.profile.repo.snapshots.select()]

            for row, snapshot in enumerate(snapshots):
                self.snapshotTable.insertRow(row)
                self.snapshotTable.setItem(row, 0, QTableWidgetItem(snapshot.name))
                self.snapshotTable.setItem(row, 1, QTableWidgetItem(pretty_bytes(snapshot.size)))
                if snapshot.duration:
                    formatted_duration = str(timedelta(seconds=round(snapshot.duration)))
                else:
                    formatted_duration = 'N/A'
                self.snapshotTable.setItem(row, 2, QTableWidgetItem(formatted_duration))
                formatted_time = snapshot.time.strftime('%Y-%m-%d %H:%M')
                self.snapshotTable.setItem(row, 3, QTableWidgetItem(formatted_time))
            self.snapshotTable.setRowCount(len(snapshots))

    def snapshot_mount(self):
        profile = self.profile
        cmd = ['borg', 'mount', '--log-json']
        row_selected = self.snapshotTable.selectionModel().selectedRows()
        if row_selected:
            snapshot_cell = self.snapshotTable.item(row_selected[0].row(), 0)
            if snapshot_cell:
                snapshot_name = snapshot_cell.text()
                cmd.append(f'{profile.repo.url}::{snapshot_name}')
            else:
                cmd.append(f'{profile.repo.url}')
        else:
            cmd.append(f'{profile.repo.url}')

        options = QFileDialog.Options()
        options |= QFileDialog.ShowDirsOnly
        options |= QFileDialog.DontUseNativeDialog
        mountPoint = QFileDialog.getExistingDirectory(
            self, "Choose Mount Point", "", options=options)
        if mountPoint:
            cmd.append(mountPoint)

            self.set_status('Mounting snapshot into folder...')
            params = {'password': keyring.get_password("vorta-repo", profile.repo.url)}
            self.snapshotMountButton.setEnabled(False)
            thread = BorgThread(cmd, params, parent=self)
            thread.updated.connect(self.mount_update_log)
            thread.result.connect(self.mount_get_result)
            thread.start()

    def mount_update_log(self, text):
        self.mountErrors.setText(text)

    def mount_get_result(self, result):
        self.snapshotMountButton.setEnabled(True)
        if result['returncode'] == 0:
            self.set_status('Mounted successfully.')

