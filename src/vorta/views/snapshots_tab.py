from datetime import timedelta
import copy
from PyQt5 import uic
from PyQt5.QtWidgets import QFileDialog, QTableWidgetItem, QTableView, QHeaderView

from vorta.borg.borg_thread import BorgThread
from vorta.borg.prune import BorgPruneThread
from vorta.borg.list import BorgListThread
from vorta.utils import get_asset, keyring, pretty_bytes
from vorta.models import BackupProfileMixin

uifile = get_asset('UI/snapshottab.ui')
SnapshotUI, SnapshotBase = uic.loadUiType(uifile)


class SnapshotTab(SnapshotBase, SnapshotUI, BackupProfileMixin):
    prune_intervals = ['hour', 'day', 'week', 'month', 'year']

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(parent)

        header = self.snapshotTable.horizontalHeader()
        header.setVisible(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)

        self.snapshotTable.setSelectionBehavior(QTableView.SelectRows)
        self.snapshotTable.setEditTriggers(QTableView.NoEditTriggers)

        # Populate pruning options from database
        for i in self.prune_intervals:
            getattr(self, f'prune_{i}').setValue(getattr(self.profile(), f'prune_{i}'))
            getattr(self, f'prune_{i}').valueChanged.connect(self.save_prune_setting)

        self.snapshotMountButton.clicked.connect(self.snapshot_mount)
        self.listButton.clicked.connect(self.list_action)
        self.pruneButton.clicked.connect(self.prune_action)

        self.populate()

    def set_status(self, text):
        self.mountErrors.setText(text)
        self.mountErrors.repaint()

    def populate(self):
        if self.profile().repo:
            snapshots = [s for s in self.profile().repo.snapshots.select()]

            for row, snapshot in enumerate(snapshots):
                self.snapshotTable.insertRow(row)
                formatted_time = snapshot.time.strftime('%Y-%m-%d %H:%M')
                self.snapshotTable.setItem(row, 0, QTableWidgetItem(formatted_time))
                self.snapshotTable.setItem(row, 1, QTableWidgetItem(pretty_bytes(snapshot.size)))
                if snapshot.duration:
                    formatted_duration = str(timedelta(seconds=round(snapshot.duration)))
                else:
                    formatted_duration = 'N/A'
                self.snapshotTable.setItem(row, 2, QTableWidgetItem(formatted_duration))
                self.snapshotTable.setItem(row, 3, QTableWidgetItem(snapshot.name))
            self.snapshotTable.setRowCount(len(snapshots))
        else:
            self.snapshotTable.setRowCount(0)

    def prune_action(self):
        params = BorgPruneThread.prepare()
        if params['ok']:
            thread = BorgPruneThread(params['cmd'], params, parent=self)
            thread.updated.connect(self.set_status)
            thread.result.connect(self.prune_result)
            self.pruneButton.setEnabled(False)
            self.listButton.setEnabled(False)
            thread.start()

    def prune_result(self, result):
        if result['returncode'] == 0:
            self.set_status('Pruning finished.')
            self.list_action()
        else:
            self.pruneButton.setEnabled(True)

    def list_action(self):
        params = BorgListThread.prepare()
        if params['ok']:
            thread = BorgListThread(params['cmd'], params, parent=self)
            thread.updated.connect(self.set_status)
            thread.result.connect(self.list_result)
            self.listButton.setEnabled(False)
            self.pruneButton.setEnabled(False)
            thread.start()

    def list_result(self, result):
        self.listButton.setEnabled(True)
        self.refreshButton.setEnabled(True)
        if result['returncode'] == 0:
            self.set_status('Refreshed snapshots.')
            self.populate()

    def snapshot_mount(self):
        profile = self.profile()
        cmd = ['borg', 'mount', '--log-json']
        row_selected = self.snapshotTable.selectionModel().selectedRows()
        if row_selected:
            snapshot_cell = self.snapshotTable.item(row_selected[0].row(), 3)
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
            params = BorgThread.prepare()
            if params['ok']:
                self.snapshotMountButton.setEnabled(False)
                thread = BorgThread(params['cmd'], params, parent=self)
                thread.updated.connect(self.mountErrors.setText)
                thread.result.connect(self.mount_get_result)
                thread.start()

    def mount_get_result(self, result):
        self.snapshotMountButton.setEnabled(True)
        if result['returncode'] == 0:
            self.set_status('Mounted successfully.')

    def save_prune_setting(self, new_value):
        profile = self.profile()
        for i in self.prune_intervals:
            setattr(profile, f'prune_{i}', getattr(self, f'prune_{i}').value())
        profile.save()
