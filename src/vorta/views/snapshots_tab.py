from datetime import timedelta
import copy
from PyQt5 import uic
from PyQt5.QtWidgets import QFileDialog, QTableWidgetItem, QTableView, QHeaderView

from vorta.borg.prune import BorgPruneThread
from vorta.borg.list import BorgListThread
from vorta.borg.check import BorgCheckThread
from vorta.borg.mount import BorgMountThread
from vorta.utils import get_asset, keyring, pretty_bytes
from vorta.models import BackupProfileMixin

uifile = get_asset('UI/snapshottab.ui')
SnapshotUI, SnapshotBase = uic.loadUiType(uifile, from_imports=True, import_from='vorta.views')


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

        self.mountButton.clicked.connect(self.mount_action)
        self.listButton.clicked.connect(self.list_action)
        self.pruneButton.clicked.connect(self.prune_action)
        self.checkButton.clicked.connect(self.check_action)

        self.populate()

    def _set_status(self, text):
        self.mountErrors.setText(text)
        self.mountErrors.repaint()

    def _toggle_all_buttons(self, enabled=True):
        self.checkButton.setEnabled(enabled)
        self.listButton.setEnabled(enabled)
        self.pruneButton.setEnabled(enabled)
        self.mountButton.setEnabled(enabled)

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


    def check_action(self):
        params = BorgCheckThread.prepare(self.profile())
        if params['ok']:
            thread = BorgCheckThread(params['cmd'], params, parent=self)
            thread.updated.connect(self._set_status)
            thread.result.connect(self.check_result)
            self._toggle_all_buttons(False)
            thread.start()

    def check_result(self, result):
        if result['returncode'] == 0:
            self._toggle_all_buttons(True)

    def prune_action(self):
        params = BorgPruneThread.prepare(self.profile())
        if params['ok']:
            thread = BorgPruneThread(params['cmd'], params, parent=self)
            thread.updated.connect(self._set_status)
            thread.result.connect(self.prune_result)
            self._toggle_all_buttons(False)
            thread.start()

    def prune_result(self, result):
        if result['returncode'] == 0:
            self._set_status('Pruning finished.')
            self.list_action()
        else:
            self._toggle_all_buttons(True)

    def list_action(self):
        params = BorgListThread.prepare(self.profile())
        if params['ok']:
            thread = BorgListThread(params['cmd'], params, parent=self)
            thread.updated.connect(self._set_status)
            thread.result.connect(self.list_result)
            self._toggle_all_buttons(False)
            thread.start()

    def list_result(self, result):
        self._toggle_all_buttons(True)
        if result['returncode'] == 0:
            self._set_status('Refreshed snapshots.')
            self.populate()

    def mount_action(self):
        profile = self.profile()
        params = BorgMountThread.prepare(profile)
        row_selected = self.snapshotTable.selectionModel().selectedRows()
        if row_selected:
            snapshot_cell = self.snapshotTable.item(row_selected[0].row(), 3)
            if snapshot_cell:
                snapshot_name = snapshot_cell.text()
                params['cmd'][-1] += f'::{snapshot_name}'

        options = QFileDialog.Options()
        options |= QFileDialog.ShowDirsOnly
        options |= QFileDialog.DontUseNativeDialog
        mountPoint = QFileDialog.getExistingDirectory(
            self, "Choose Mount Point", "", options=options)
        if mountPoint:
            params['cmd'].append(mountPoint)
            if params['ok']:
                self._toggle_all_buttons(False)
                thread = BorgMountThread(params['cmd'], params, parent=self)
                thread.updated.connect(self.mountErrors.setText)
                thread.result.connect(self.mount_result)
                thread.start()

    def mount_result(self, result):
        self._toggle_all_buttons(True)
        if result['returncode'] == 0:
            self._set_status('Mounted successfully.')

    def save_prune_setting(self, new_value):
        profile = self.profile()
        for i in self.prune_intervals:
            setattr(profile, f'prune_{i}', getattr(self, f'prune_{i}').value())
        profile.save()
