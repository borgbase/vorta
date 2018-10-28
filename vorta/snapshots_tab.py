import os
from PyQt5 import uic, QtCore
from PyQt5.QtWidgets import QFileDialog, QTableWidgetItem, QTableView, QHeaderView

from .borg_runner import BorgThread
from .utils import get_relative_asset

uifile = get_relative_asset('UI/snapshottab.ui')
SnapshotUI, SnapshotBase = uic.loadUiType(uifile)


class SnapshotTab(SnapshotBase, SnapshotUI):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(parent)
        self.profile = self.window().profile

        header = self.snapshotTable.horizontalHeader()
        header.setVisible(True)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)

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
                formatted_time = snapshot.time.strftime('%Y-%m-%d %H:%M')
                self.snapshotTable.setItem(row, 1, QTableWidgetItem(formatted_time))
            self.snapshotTable.setRowCount(len(snapshots))

    def snapshot_mount(self):
        cmd = ['borg', 'mount', '--log-json']
        row_selected = self.snapshotTable.selectionModel().selectedRows()
        if row_selected:
            snapshot_cell = self.snapshotTable.item(row_selected[0].row(), 0)
            if snapshot_cell:
                snapshot_name = snapshot_cell.text()
                cmd.append(f'{self.profile.repo.url}::{snapshot_name}')
            else:
                cmd.append(f'{self.profile.repo.url}')
        else:
            cmd.append(f'{self.profile.repo.url}')

        options = QFileDialog.Options()
        options |= QFileDialog.ShowDirsOnly
        options |= QFileDialog.DontUseNativeDialog
        mountPoint = QFileDialog.getExistingDirectory(
            self, "Choose Mount Point", "", options=options)
        if mountPoint:
            cmd.append(mountPoint)

            self.set_status('Mounting snapshot into folder...')
            params = {'password': self.profile.repo.password}
            thread = BorgThread(self, cmd, params)
            thread.updated.connect(self.mount_update_log)
            thread.result.connect(self.mount_get_result)
            thread.start()

    def mount_update_log(self, text):
        self.mountErrors.setText(text)

    def mount_get_result(self, result):
        if result['returncode'] == 0:
            self.set_status('Mounted successfully.')
