import sys
from datetime import timedelta
from PyQt5 import uic, QtCore
from PyQt5.QtWidgets import QTableWidgetItem, QTableView, QHeaderView

from vorta.borg.prune import BorgPruneThread
from vorta.borg.list_repo import BorgListRepoThread
from vorta.borg.list_archive import BorgListArchiveThread
from vorta.borg.check import BorgCheckThread
from vorta.borg.mount import BorgMountThread
from vorta.borg.extract import BorgExtractThread
from vorta.borg.umount import BorgUmountThread
from vorta.views.extract_dialog import ExtractDialog
from vorta.utils import get_asset, pretty_bytes, choose_file_dialog
from vorta.models import BackupProfileMixin, ArchiveModel

uifile = get_asset('UI/archivetab.ui')
ArchiveTabUI, ArchiveTabBase = uic.loadUiType(uifile, from_imports=True, import_from='vorta.views')


class ArchiveTab(ArchiveTabBase, ArchiveTabUI, BackupProfileMixin):
    prune_intervals = ['hour', 'day', 'week', 'month', 'year']

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(parent)
        self.mount_point = None

        header = self.archiveTable.horizontalHeader()
        header.setVisible(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setStretchLastSection(True)

        if sys.platform != 'darwin':
            self._set_status('')  # Set platform-specific hints.

        self.archiveTable.setSelectionBehavior(QTableView.SelectRows)
        self.archiveTable.setEditTriggers(QTableView.NoEditTriggers)
        self.archiveTable.setAlternatingRowColors(True)

        # Populate pruning options from database
        profile = self.profile()
        for i in self.prune_intervals:
            getattr(self, f'prune_{i}').setValue(getattr(profile, f'prune_{i}'))
            getattr(self, f'prune_{i}').valueChanged.connect(self.save_prune_setting)
        self.prune_keep_within.setText(profile.prune_keep_within)
        self.prune_keep_within.editingFinished.connect(self.save_prune_setting)

        self.mountButton.clicked.connect(self.mount_action)
        self.listButton.clicked.connect(self.list_action)
        self.pruneButton.clicked.connect(self.prune_action)
        self.checkButton.clicked.connect(self.check_action)
        self.extractButton.clicked.connect(self.list_archive_action)

        self.populate_from_profile()

    def _set_status(self, text):
        self.mountErrors.setText(text)
        self.mountErrors.repaint()

    def _toggle_all_buttons(self, enabled=True):
        for button in [self.checkButton, self.listButton, self.pruneButton, self.mountButton, self.extractButton]:
            button.setEnabled(enabled)
            button.repaint()

    def populate_from_profile(self):
        """Populate archive list and prune settings from profile."""

        profile = self.profile()
        if profile.repo is not None:
            self.currentRepoLabel.setText(profile.repo.url)
            archives = [s for s in profile.repo.archives.select().order_by(ArchiveModel.time.desc())]

            for row, archive in enumerate(archives):
                self.archiveTable.insertRow(row)

                formatted_time = archive.time.strftime('%Y-%m-%d %H:%M')
                self.archiveTable.setItem(row, 0, QTableWidgetItem(formatted_time))
                self.archiveTable.setItem(row, 1, QTableWidgetItem(pretty_bytes(archive.size)))
                if archive.duration is not None:
                    formatted_duration = str(timedelta(seconds=round(archive.duration)))
                else:
                    formatted_duration = ''
                self.archiveTable.setItem(row, 2, QTableWidgetItem(formatted_duration))
                self.archiveTable.setItem(row, 3, QTableWidgetItem(archive.name))
            self.archiveTable.setRowCount(len(archives))
            item = self.archiveTable.item(0, 0)
            self.archiveTable.scrollToItem(item)
            self._toggle_all_buttons(enabled=True)
        else:
            self.archiveTable.setRowCount(0)
            self.currentRepoLabel.setText('N/A')
            self._toggle_all_buttons(enabled=False)

    def check_action(self):
        params = BorgCheckThread.prepare(self.profile())
        if not params['ok']:
            self._set_status(params['message'])
            return

        # Conditions are met (borg binary available, etc)
        row_selected = self.archiveTable.selectionModel().selectedRows()
        if row_selected:
            snapshot_cell = self.archiveTable.item(row_selected[0].row(), 3)
            if snapshot_cell:
                snapshot_name = snapshot_cell.text()
                params['cmd'][-1] += f'::{snapshot_name}'

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
        params = BorgListRepoThread.prepare(self.profile())
        if params['ok']:
            thread = BorgListRepoThread(params['cmd'], params, parent=self)
            thread.updated.connect(self._set_status)
            thread.result.connect(self.list_result)
            self._toggle_all_buttons(False)
            thread.start()

    def list_result(self, result):
        self._toggle_all_buttons(True)
        if result['returncode'] == 0:
            self._set_status('Refreshed snapshots.')
            self.populate_from_profile()

    def mount_action(self):
        profile = self.profile()
        params = BorgMountThread.prepare(profile)
        if not params['ok']:
            self._set_status(params['message'])
            return

        # Conditions are met (borg binary available, etc)
        row_selected = self.archiveTable.selectionModel().selectedRows()
        if row_selected:
            snapshot_cell = self.archiveTable.item(row_selected[0].row(), 3)
            if snapshot_cell:
                snapshot_name = snapshot_cell.text()
                params['cmd'][-1] += f'::{snapshot_name}'

        def receive():
            mount_point = dialog.selectedFiles()
            if mount_point:
                params['cmd'].append(mount_point[0])
                self.mount_point = mount_point[0]
                if params['ok']:
                    self._toggle_all_buttons(False)
                    thread = BorgMountThread(params['cmd'], params, parent=self)
                    thread.updated.connect(self.mountErrors.setText)
                    thread.result.connect(self.mount_result)
                    thread.start()

        dialog = choose_file_dialog(self, "Choose Mount Point")
        dialog.open(receive)

    def mount_result(self, result):
        self._toggle_all_buttons(True)
        if result['returncode'] == 0:
            self._set_status('Mounted successfully.')
            self.mountButton.setText('Unmount')
            self.mountButton.clicked.disconnect()
            self.mountButton.clicked.connect(self.umount_action)
        else:
            self.mount_point = None

    def umount_action(self):
        if self.mount_point is not None:
            profile = self.profile()
            params = BorgUmountThread.prepare(profile)
            if not params['ok']:
                self._set_status(params['message'])
                return

            if self.mount_point in params['active_mount_points']:
                params['cmd'].append(self.mount_point)
                thread = BorgUmountThread(params['cmd'], params, parent=self)
                thread.updated.connect(self.mountErrors.setText)
                thread.result.connect(self.umount_result)
                thread.start()
            else:
                self._set_status('Mount point not active. Try restarting Vorta.')
                return

    def umount_result(self, result):
        self._toggle_all_buttons(True)
        if result['returncode'] == 0:
            self._set_status('Un-mounted successfully.')
            self.mountButton.setText('Mount')
            self.mountButton.clicked.disconnect()
            self.mountButton.clicked.connect(self.mount_action)
            self.mount_point = None

    def save_prune_setting(self, new_value=None):
        profile = self.profile()
        for i in self.prune_intervals:
            setattr(profile, f'prune_{i}', getattr(self, f'prune_{i}').value())
        profile.prune_keep_within = self.prune_keep_within.text()
        profile.save()

    def list_archive_action(self):
        profile = self.profile()

        row_selected = self.archiveTable.selectionModel().selectedRows()
        if row_selected:
            archive_cell = self.archiveTable.item(row_selected[0].row(), 3)
            if archive_cell:
                archive_name = archive_cell.text()
                params = BorgListArchiveThread.prepare(profile)

                if not params['ok']:
                    self._set_status(params['message'])
                    return
                params['cmd'][-1] += f'::{archive_name}'
                params['archive_name'] = archive_name
                self._set_status('')
                self._toggle_all_buttons(False)

                thread = BorgListArchiveThread(params['cmd'], params, parent=self)
                thread.updated.connect(self.mountErrors.setText)
                thread.result.connect(self.list_archive_result)
                thread.start()
        else:
            self._set_status('Select an archive to restore first.')

    def list_archive_result(self, result):
        self._set_status('')
        if result['returncode'] == 0:
            archive = ArchiveModel.get(name=result['params']['archive_name'])
            window = ExtractDialog(result['data'], archive)
            self._toggle_all_buttons(True)
            window.setParent(self, QtCore.Qt.Sheet)
            self._window = window  # for testing
            window.show()

            if window.exec_():
                def receive():
                    extraction_folder = dialog.selectedFiles()
                    if extraction_folder:
                        params = BorgExtractThread.prepare(
                            self.profile(), archive.name, window.selected, extraction_folder[0])
                        if params['ok']:
                            self._toggle_all_buttons(False)
                            thread = BorgExtractThread(params['cmd'], params, parent=self)
                            thread.updated.connect(self.mountErrors.setText)
                            thread.result.connect(self.extract_archive_result)
                            thread.start()
                        else:
                            self._set_status(params['message'])

                dialog = choose_file_dialog(self, "Choose Extraction Point")
                dialog.open(receive)

    def extract_archive_result(self, result):
        self._toggle_all_buttons(True)
