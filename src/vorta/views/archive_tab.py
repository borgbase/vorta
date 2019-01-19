import os.path
import sys
from datetime import timedelta
from PyQt5 import uic, QtCore
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QTableWidgetItem, QTableView, QHeaderView, QMenu

from vorta.borg.prune import BorgPruneThread
from vorta.borg.list_repo import BorgListRepoThread
from vorta.borg.list_archive import BorgListArchiveThread
from vorta.borg.check import BorgCheckThread
from vorta.borg.mount import BorgMountThread
from vorta.borg.extract import BorgExtractThread
from vorta.borg.umount import BorgUmountThread
from vorta.views.extract_dialog import ExtractDialog
from vorta.utils import get_asset, pretty_bytes, choose_file_dialog, format_archive_name, open_folder, \
    get_mount_points
from vorta.models import BackupProfileMixin, ArchiveModel

uifile = get_asset('UI/archivetab.ui')
ArchiveTabUI, ArchiveTabBase = uic.loadUiType(uifile, from_imports=True, import_from='vorta.views')


class ArchiveTab(ArchiveTabBase, ArchiveTabUI, BackupProfileMixin):
    prune_intervals = ['hour', 'day', 'week', 'month', 'year']

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(parent)
        self.mount_points = {}
        self.menu = None
        self.toolBox.setCurrentIndex(0)

        self.folder_icon = QIcon(':/icons/folder-open.svg')
        self.archiveTable.setHorizontalHeaderItem(3, QTableWidgetItem(self.folder_icon, ''))
        header = self.archiveTable.horizontalHeader()
        header.setVisible(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setMinimumSectionSize(32)
        header.resizeSection(3, 32)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setStretchLastSection(True)

        if sys.platform != 'darwin':
            self._set_status('')  # Set platform-specific hints.

        self.archiveTable.setSelectionBehavior(QTableView.SelectRows)
        self.archiveTable.setSelectionMode(QTableView.SingleSelection)
        self.archiveTable.setEditTriggers(QTableView.NoEditTriggers)
        self.archiveTable.setAlternatingRowColors(True)
        self.archiveTable.itemSelectionChanged.connect(self.update_mount_button_text)
        self.archiveTable.installEventFilter(self)

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

        self.archiveNameTemplate.textChanged.connect(
            lambda tpl, key='new_archive_name': self.save_archive_template(tpl, key))
        self.prunePrefixTemplate.textChanged.connect(
            lambda tpl, key='prune_prefix': self.save_archive_template(tpl, key))

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
        self.mount_points = get_mount_points(profile.repo.url)
        if profile.repo is not None:
            self.toolBox.setItemText(0, f'Archives for {profile.repo.url}')
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
                mount_point = self.mount_points.get(archive.name)
                if mount_point is not None:
                    item = QTableWidgetItem(self.folder_icon, '')
                else:
                    item = QTableWidgetItem('')
                self.archiveTable.setItem(row, 3, item)
                self.archiveTable.setItem(row, 4, QTableWidgetItem(archive.name))
            self.archiveTable.setRowCount(len(archives))
            item = self.archiveTable.item(0, 0)
            self.archiveTable.scrollToItem(item)
            self._toggle_all_buttons(enabled=True)
        else:
            self.archiveTable.setRowCount(0)
            self.toolBox.setItemText(0, 'Archives')
            self._toggle_all_buttons(enabled=False)

        self.archiveNameTemplate.setText(profile.new_archive_name)
        self.prunePrefixTemplate.setText(profile.prune_prefix)

    def save_archive_template(self, tpl, key):
        profile = self.profile()
        try:
            preview = 'Preview: ' + format_archive_name(profile, tpl)
            setattr(profile, key, tpl)
            profile.save()
        except Exception:
            preview = 'Error in archive name template.'

        if key == 'new_archive_name':
            self.archiveNamePreview.setText(preview)
        else:
            self.prunePrefixPreview.setText(preview)

    def check_action(self):
        params = BorgCheckThread.prepare(self.profile())
        if not params['ok']:
            self._set_status(params['message'])
            return

        # Conditions are met (borg binary available, etc)
        row_selected = self.archiveTable.selectionModel().selectedRows()
        if row_selected:
            snapshot_cell = self.archiveTable.item(row_selected[0].row(), 4)
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

    def selected_archive_name(self):
        row_selected = self.archiveTable.selectionModel().selectedRows()
        if row_selected:
            snapshot_cell = self.archiveTable.item(row_selected[0].row(), 4)
            if snapshot_cell:
                return snapshot_cell.text()
        return None

    def set_mount_button_mode(self, mode):
        self.mountButton.clicked.disconnect()
        if mode == 'Mount':
            self.mountButton.setText('Mount')
            self.mountButton.clicked.connect(self.mount_action)
        elif mode == 'Unmount':
            self.mountButton.setText('Unmount')
            self.mountButton.clicked.connect(self.umount_action)

    def mount_action(self):
        profile = self.profile()
        params = BorgMountThread.prepare(profile)
        if not params['ok']:
            self._set_status(params['message'])
            return

        # Conditions are met (borg binary available, etc)
        snapshot_name = self.selected_archive_name()
        if snapshot_name:
            params['cmd'][-1] += f'::{snapshot_name}'
            params['current_archive'] = snapshot_name

        def receive():
            mount_point = dialog.selectedFiles()
            if mount_point:
                params['cmd'].append(mount_point[0])
                self.mount_points[params['current_archive']] = mount_point[0]
                if params['ok']:
                    self._toggle_all_buttons(False)
                    thread = BorgMountThread(params['cmd'], params, parent=self)
                    thread.updated.connect(self.mountErrors.setText)
                    thread.result.connect(self.mount_result)
                    thread.start()

        dialog = choose_file_dialog(self, "Choose Mount Point", want_folder=True)
        dialog.open(receive)

    def mount_result(self, result):
        self._toggle_all_buttons(True)
        if result['returncode'] == 0:
            self._set_status('Mounted successfully.')
            self.update_mount_button_text()
            archive_name = result['params']['current_archive']
            row = self.row_of_archive(archive_name)
            item = QTableWidgetItem(self.folder_icon, '')
            self.archiveTable.setItem(row, 3, item)

    def umount_action(self):
        snapshot_name = self.selected_archive_name()

        mount_point = self.mount_points.get(snapshot_name)

        if mount_point is not None:
            profile = self.profile()
            params = BorgUmountThread.prepare(profile)
            if not params['ok']:
                self._set_status(params['message'])
                return

            params['current_archive'] = snapshot_name

            if os.path.normpath(mount_point) in params['active_mount_points']:
                params['cmd'].append(mount_point)
                thread = BorgUmountThread(params['cmd'], params, parent=self)
                thread.updated.connect(self.mountErrors.setText)
                thread.result.connect(self.umount_result)
                thread.start()
            else:
                self._set_status('Mount point not active.')
                return

    def umount_result(self, result):
        self._toggle_all_buttons(True)
        if result['returncode'] == 0:
            self._set_status('Un-mounted successfully.')
            archive_name = result['params']['current_archive']
            del self.mount_points[archive_name]
            self.update_mount_button_text()
            row = self.row_of_archive(archive_name)
            item = QTableWidgetItem('')
            self.archiveTable.setItem(row, 3, item)

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
            archive_cell = self.archiveTable.item(row_selected[0].row(), 4)
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

                dialog = choose_file_dialog(self, "Choose Extraction Point", want_folder=True)
                dialog.open(receive)

    def extract_archive_result(self, result):
        self._toggle_all_buttons(True)

    def update_mount_button_text(self):
        snapshot_name = self.selected_archive_name()
        if not snapshot_name:
            return

        mode = 'Unmount' if snapshot_name in self.mount_points else 'Mount'
        self.set_mount_button_mode(mode)

    def open_folder_action(self):
        snapshot_name = self.selected_archive_name()
        if not snapshot_name:
            return

        mount_point = self.mount_points.get(snapshot_name)

        if mount_point is not None:
            open_folder(mount_point)

    def eventFilter(self, obj, event):
        if obj == self.archiveTable and event.type() == QtCore.QEvent.ContextMenu:
            self.archiveTable_context_menu_event(event)
            return True

        return super(ArchiveTabBase, self).eventFilter(obj, event)

    def archiveTable_context_menu_event(self, event):
        snapshot_name = self.selected_archive_name()
        if not snapshot_name or not self.archiveTable.indexAt(event.pos()).isValid():
            event.ignore()
            return

        if not self.menu:
            self.menu = QMenu(self)
        else:
            self.menu.clear()

        if snapshot_name in self.mount_points:
            open_folder = self.menu.addAction("Open Folder...")
            open_folder.triggered.connect(self.open_folder_action)
            self.menu.addSeparator()

        extract_action = self.menu.addAction("Extract...")
        extract_action.triggered.connect(self.list_archive_action)
        extract_action.setEnabled(self.extractButton.isEnabled())

        if snapshot_name in self.mount_points:
            mount_action = self.menu.addAction("Unmount")
            mount_action.triggered.connect(self.umount_action)
        else:
            mount_action = self.menu.addAction("Mount...")
            mount_action.triggered.connect(self.mount_action)
        mount_action.setEnabled(self.mountButton.isEnabled())

        check_action = self.menu.addAction("Check")
        check_action.triggered.connect(self.check_action)
        check_action.setEnabled(self.checkButton.isEnabled())

        self.menu.exec(event.globalPos())

        event.accept()

    def row_of_archive(self, archive_name):
        items = self.archiveTable.findItems(archive_name, QtCore.Qt.MatchExactly)
        rows = [item.row() for item in items if item.column() == 4]
        if rows == []:
            return None

        return rows[0]
