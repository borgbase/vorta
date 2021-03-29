import os.path
import sys
from datetime import timedelta

from PyQt5 import QtCore, uic
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (QHeaderView, QMessageBox, QTableView,
                             QTableWidgetItem, QInputDialog, QMenu,
                             QToolButton)

from vorta.borg.check import BorgCheckThread
from vorta.borg.delete import BorgDeleteThread
from vorta.borg.diff import BorgDiffThread
from vorta.borg.extract import BorgExtractThread
from vorta.borg.list_archive import BorgListArchiveThread
from vorta.borg.list_repo import BorgListRepoThread
from vorta.borg.info_archive import BorgInfoArchiveThread
from vorta.borg.mount import BorgMountThread
from vorta.borg.prune import BorgPruneThread
from vorta.borg.umount import BorgUmountThread
from vorta.borg.rename import BorgRenameThread
from vorta.i18n import trans_late
from vorta.models import ArchiveModel, BackupProfileMixin
from vorta.utils import (choose_file_dialog, format_archive_name, get_asset,
                         get_mount_points, pretty_bytes)
from vorta.views.source_tab import SizeItem
from vorta.views.diff_dialog import DiffDialog
from vorta.views.diff_result import DiffResult
from vorta.views.extract_dialog import ExtractDialog
from vorta.views.utils import get_colored_icon

uifile = get_asset('UI/archivetab.ui')
ArchiveTabUI, ArchiveTabBase = uic.loadUiType(uifile)


class ArchiveTab(ArchiveTabBase, ArchiveTabUI, BackupProfileMixin):
    prune_intervals = ['hour', 'day', 'week', 'month', 'year']

    def __init__(self, parent=None, app=None):
        super().__init__(parent)
        self.setupUi(parent)
        self.mount_points = {}
        self.menu = None
        self.app = app
        self.toolBox.setCurrentIndex(0)

        header = self.archiveTable.horizontalHeader()
        header.setVisible(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setStretchLastSection(True)

        if sys.platform != 'darwin':
            self._set_status('')  # Set platform-specific hints.

        self.archiveTable.setSelectionBehavior(QTableView.SelectRows)
        self.archiveTable.setSelectionMode(QTableView.SingleSelection)
        self.archiveTable.setEditTriggers(QTableView.NoEditTriggers)
        self.archiveTable.setWordWrap(False)
        self.archiveTable.setTextElideMode(QtCore.Qt.ElideLeft)
        self.archiveTable.setAlternatingRowColors(True)
        self.archiveTable.cellDoubleClicked.connect(self.cell_double_clicked)
        self.archiveTable.setSortingEnabled(True)

        self.listButton.clicked.connect(self.list_action)
        self.pruneButton.clicked.connect(self.prune_action)
        self.checkButton.clicked.connect(self.check_action)
        self.diffButton.clicked.connect(self.diff_action)

        self.archiveActionMenu = QMenu(parent=self)
        self.archiveActionMenu.aboutToShow.connect(self.showArchiveActionMenu)
        self.archiveActionButton.setMenu(self.archiveActionMenu)
        self.archiveActionButton.setPopupMode(QToolButton.InstantPopup)

        self.archiveNameTemplate.textChanged.connect(
            lambda tpl, key='new_archive_name': self.save_archive_template(tpl, key))
        self.prunePrefixTemplate.textChanged.connect(
            lambda tpl, key='prune_prefix': self.save_archive_template(tpl, key))

        self.populate_from_profile()
        self.selected_archives = None
        self.set_icons()

    def set_icons(self):
        "Used when changing between light- and dark mode"
        self.checkButton.setIcon(get_colored_icon('check-circle'))
        self.diffButton.setIcon(get_colored_icon('stream-solid'))
        self.pruneButton.setIcon(get_colored_icon('cut'))
        self.listButton.setIcon(get_colored_icon('refresh'))
        self.toolBox.setItemIcon(0, get_colored_icon('tasks'))
        self.toolBox.setItemIcon(1, get_colored_icon('cut'))
        self.archiveActionButton.setIcon(get_colored_icon('ellipsis-v'))

    def cancel_action(self):
        self._set_status(self.tr("Action cancelled."))
        self._toggle_all_buttons(True)

    def _set_status(self, text):
        self.mountErrors.setText(text)
        self.mountErrors.repaint()

    def _toggle_all_buttons(self, enabled=True):
        for button in [self.checkButton, self.listButton, self.pruneButton,
                       self.diffButton, self.archiveActionButton]:
            button.setEnabled(enabled)
            button.repaint()

    def showArchiveActionMenu(self):
        archive_name = self.selected_archive_name()
        menu = self.archiveActionMenu
        menu.clear()

        if not archive_name:
            action = menu.addAction(self.tr("Select an archive first."))
            action.setEnabled(False)
            return menu

        if archive_name in self.mount_points:
            unmountAction = menu.addAction("Unmount", self.umount_action)
            unmountAction.setIcon(get_colored_icon('eject'))
        else:
            mountAction = menu.addAction("Mount", self.mount_action)
            mountAction.setIcon(get_colored_icon('folder-open'))

        extractAction = menu.addAction("Extract", self.list_archive_action)
        refreshAction = menu.addAction("Refresh", self.refresh_archive_action)
        renameAction = menu.addAction("Rename", self.rename_action)
        deleteAction = menu.addAction("Delete", self.delete_action)

        extractAction.setIcon(get_colored_icon('cloud-download'))
        refreshAction.setIcon(get_colored_icon('refresh'))
        renameAction.setIcon(get_colored_icon('edit'))
        deleteAction.setIcon(get_colored_icon('trash'))
        return menu

    def populate_from_profile(self):
        """Populate archive list and prune settings from profile."""
        profile = self.profile()
        if profile.repo is not None:
            self.mount_points = get_mount_points(profile.repo.url)
            self.toolBox.setItemText(0, self.tr('Archives for %s') % profile.repo.url)
            archives = [s for s in profile.repo.archives.select().order_by(ArchiveModel.time.desc())]

            sorting = self.archiveTable.isSortingEnabled()
            self.archiveTable.setSortingEnabled(False)
            for row, archive in enumerate(archives):
                self.archiveTable.insertRow(row)

                formatted_time = archive.time.strftime('%Y-%m-%d %H:%M')
                self.archiveTable.setItem(row, 0, QTableWidgetItem(formatted_time))
                self.archiveTable.setItem(row, 1, SizeItem(pretty_bytes(archive.size)))
                if archive.duration is not None:
                    formatted_duration = str(timedelta(seconds=round(archive.duration)))
                else:
                    formatted_duration = ''

                self.archiveTable.setItem(row, 2, QTableWidgetItem(formatted_duration))

                mount_point = self.mount_points.get(archive.name)
                if mount_point is not None:
                    item = QTableWidgetItem(mount_point)
                    self.archiveTable.setItem(row, 3, item)

                self.archiveTable.setItem(row, 4, QTableWidgetItem(archive.name))

            self.archiveTable.setRowCount(len(archives))
            self.archiveTable.setSortingEnabled(sorting)
            item = self.archiveTable.item(0, 0)
            self.archiveTable.scrollToItem(item)
            self._toggle_all_buttons(enabled=True)
        else:
            self.mount_points = {}
            self.archiveTable.setRowCount(0)
            self.toolBox.setItemText(0, self.tr('Archives'))
            self._toggle_all_buttons(enabled=False)

        self.archiveNameTemplate.setText(profile.new_archive_name)
        self.prunePrefixTemplate.setText(profile.prune_prefix)

        # Populate pruning options from database
        profile = self.profile()
        for i in self.prune_intervals:
            getattr(self, f'prune_{i}').setValue(getattr(profile, f'prune_{i}'))
            getattr(self, f'prune_{i}').valueChanged.connect(self.save_prune_setting)
        self.prune_keep_within.setText(profile.prune_keep_within)
        self.prune_keep_within.editingFinished.connect(self.save_prune_setting)

    def save_archive_template(self, tpl, key):
        profile = self.profile()
        try:
            preview = self.tr('Preview: %s') % format_archive_name(profile, tpl)
            setattr(profile, key, tpl)
            profile.save()
        except Exception:
            preview = self.tr('Error in archive name template.')

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
            archive_cell = self.archiveTable.item(row_selected[0].row(), 4)
            if archive_cell:
                archive_name = archive_cell.text()
                params['cmd'][-1] += f'::{archive_name}'

        thread = BorgCheckThread(params['cmd'], params, parent=self.app)
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
            thread = BorgPruneThread(params['cmd'], params, parent=self.app)
            thread.updated.connect(self._set_status)
            thread.result.connect(self.prune_result)
            self._toggle_all_buttons(False)
            thread.start()
        else:
            self._set_status(params['message'])

    def prune_result(self, result):
        if result['returncode'] == 0:
            self._set_status(self.tr('Pruning finished.'))
            self.list_action()
        else:
            self._toggle_all_buttons(True)

    def list_action(self):
        params = BorgListRepoThread.prepare(self.profile())
        if params['ok']:
            thread = BorgListRepoThread(params['cmd'], params, parent=self.app)
            thread.updated.connect(self._set_status)
            thread.result.connect(self.list_result)
            self._toggle_all_buttons(False)
            thread.start()
        else:
            self._set_status(params['message'])

    def list_result(self, result):
        self._toggle_all_buttons(True)
        if result['returncode'] == 0:
            self._set_status(self.tr('Refreshed archives.'))
            self.populate_from_profile()

    def refresh_archive_action(self):
        archive_name = self.selected_archive_name()
        if archive_name is not None:
            params = BorgInfoArchiveThread.prepare(self.profile(), archive_name)
            if params['ok']:
                thread = BorgInfoArchiveThread(params['cmd'], params, parent=self.app)
                thread.updated.connect(self._set_status)
                thread.result.connect(self.refresh_archive_result)
                self._toggle_all_buttons(False)
                thread.start()

    def refresh_archive_result(self, result):
        self._toggle_all_buttons(True)
        if result['returncode'] == 0:
            self._set_status(self.tr('Refreshed archive.'))
            self.populate_from_profile()

    def selected_archive_name(self):
        row_selected = self.archiveTable.selectionModel().selectedRows()
        if row_selected:
            archive_cell = self.archiveTable.item(row_selected[0].row(), 4)
            if archive_cell:
                return archive_cell.text()
        return None

    def mount_action(self):
        profile = self.profile()
        params = BorgMountThread.prepare(profile)
        if not params['ok']:
            self._set_status(params['message'])
            return

        # Conditions are met (borg binary available, etc)
        archive_name = self.selected_archive_name()
        if archive_name:
            params['cmd'][-1] += f'::{archive_name}'
            params['current_archive'] = archive_name

        def receive():
            mount_point = dialog.selectedFiles()
            if mount_point:
                params['cmd'].append(mount_point[0])
                if params.get('current_archive', False):
                    self.mount_points[params['current_archive']] = mount_point[0]
                if params['ok']:
                    self._toggle_all_buttons(False)
                    thread = BorgMountThread(params['cmd'], params, parent=self.app)
                    thread.updated.connect(self.mountErrors.setText)
                    thread.result.connect(self.mount_result)
                    thread.start()

        dialog = choose_file_dialog(self, self.tr("Choose Mount Point"), want_folder=True)
        dialog.open(receive)

    def mount_result(self, result):
        self._toggle_all_buttons(True)
        if result['returncode'] == 0:
            self._set_status(self.tr('Mounted successfully.'))
            if result['params'].get('current_archive'):
                archive_name = result['params']['current_archive']
                row = self.row_of_archive(archive_name)
                item = QTableWidgetItem(result['cmd'][-1])
                self.archiveTable.setItem(row, 3, item)

    def umount_action(self):
        archive_name = self.selected_archive_name()
        mount_point = self.mount_points.get(archive_name)

        if mount_point is not None:
            profile = self.profile()
            params = BorgUmountThread.prepare(profile)
            if not params['ok']:
                self._set_status(params['message'])
                return

            params['current_archive'] = archive_name

            if os.path.normpath(mount_point) in params['active_mount_points']:
                params['cmd'].append(mount_point)
                thread = BorgUmountThread(params['cmd'], params, parent=self.app)
                thread.updated.connect(self.mountErrors.setText)
                thread.result.connect(self.umount_result)
                thread.start()
            else:
                self._set_status(self.tr('Mount point not active.'))
                return

    def umount_result(self, result):
        self._toggle_all_buttons(True)
        archive_name = result['params']['current_archive']
        if result['returncode'] == 0:
            self._set_status(self.tr('Un-mounted successfully.'))
            del self.mount_points[archive_name]
            row = self.row_of_archive(archive_name)
            item = QTableWidgetItem('')
            self.archiveTable.setItem(row, 3, item)
        else:
            self._set_status(self.tr('Unmounting failed. Make sure no programs are using {}').format(
                self.mount_points.get(archive_name)))

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
                params = BorgListArchiveThread.prepare(profile, archive_name)

                if not params['ok']:
                    self._set_status(params['message'])
                    return
                self._set_status('')
                self._toggle_all_buttons(False)

                thread = BorgListArchiveThread(params['cmd'], params, parent=self.app)
                thread.updated.connect(self.mountErrors.setText)
                thread.result.connect(self.list_archive_result)
                thread.start()
        else:
            self._set_status(self.tr('Select an archive to restore first.'))

    def list_archive_result(self, result):
        self._set_status('')
        if result['returncode'] == 0:
            def process_result():
                def receive():
                    extraction_folder = dialog.selectedFiles()
                    if extraction_folder:
                        params = BorgExtractThread.prepare(
                            self.profile(), archive.name, window.selected, extraction_folder[0])
                        if params['ok']:
                            self._toggle_all_buttons(False)
                            thread = BorgExtractThread(params['cmd'], params, parent=self.app)
                            thread.updated.connect(self.mountErrors.setText)
                            thread.result.connect(self.extract_archive_result)
                            thread.start()
                        else:
                            self._set_status(params['message'])

                dialog = choose_file_dialog(self, self.tr("Choose Extraction Point"), want_folder=True)
                dialog.open(receive)

            archive = ArchiveModel.get(name=result['params']['archive_name'])
            window = ExtractDialog(result['data'], archive)
            self._toggle_all_buttons(True)
            window.setParent(self, QtCore.Qt.Sheet)
            self._window = window  # for testing
            window.show()
            window.accepted.connect(process_result)

    def extract_archive_result(self, result):
        self._toggle_all_buttons(True)

    def cell_double_clicked(self, row, column):
        if column == 3:
            archive_name = self.selected_archive_name()
            if not archive_name:
                return

            mount_point = self.mount_points.get(archive_name)

            if mount_point is not None:
                QDesktopServices.openUrl(QtCore.QUrl(f'file:///{mount_point}'))

    def row_of_archive(self, archive_name):
        items = self.archiveTable.findItems(archive_name, QtCore.Qt.MatchExactly)
        rows = [item.row() for item in items if item.column() == 4]
        return rows[0] if rows else None

    def confirm_dialog(self, title, text):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText(text)
        msg.setWindowTitle(title)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        msg.button(msg.Yes).setText(self.tr("Yes"))
        msg.button(msg.Cancel).setText(self.tr("Cancel"))
        return msg.exec_() == QMessageBox.Yes

    def delete_action(self):
        params = BorgDeleteThread.prepare(self.profile())
        if not params['ok']:
            self._set_status(params['message'])
            return

        self.archive_name = self.selected_archive_name()
        if self.archive_name is not None:
            if not self.confirm_dialog(trans_late('ArchiveTab', "Confirm deletion"),
                                       trans_late('ArchiveTab', "Are you sure you want to delete the archive?")):
                return
            params['cmd'][-1] += f'::{self.archive_name}'

            thread = BorgDeleteThread(params['cmd'], params, parent=self.app)
            thread.updated.connect(self._set_status)
            thread.result.connect(self.delete_result)
            self._toggle_all_buttons(False)
            thread.start()
        else:
            self._set_status(self.tr("No archive selected"))

    def delete_result(self, result):
        if result['returncode'] == 0:
            self._set_status(self.tr('Archive deleted.'))
            deleted_row = self.archiveTable.findItems(self.archive_name, QtCore.Qt.MatchExactly)[0].row()
            self.archiveTable.removeRow(deleted_row)
            ArchiveModel.get(name=self.archive_name).delete_instance()
            del self.archive_name
        else:
            self._toggle_all_buttons(True)

    def diff_action(self):
        def process_result():
            if window.selected_archives:
                self.selected_archives = window.selected_archives
            archive_cell_newer = self.archiveTable.item(self.selected_archives[0], 4)
            archive_cell_older = self.archiveTable.item(self.selected_archives[1], 4)
            if archive_cell_older and archive_cell_newer:
                archive_name_newer = archive_cell_newer.text()
                archive_name_older = archive_cell_older.text()

                params = BorgDiffThread.prepare(profile, archive_name_older, archive_name_newer)

                if params['ok']:
                    self._toggle_all_buttons(False)
                    thread = BorgDiffThread(params['cmd'], params, parent=self.app)
                    thread.updated.connect(self.mountErrors.setText)
                    thread.result.connect(self.list_diff_result)
                    thread.start()
                else:
                    self._set_status(params['message'])

        profile = self.profile()

        window = DiffDialog(self.archiveTable)
        self._toggle_all_buttons(True)
        window.setParent(self, QtCore.Qt.Sheet)
        self._window = window  # for testing
        window.show()
        window.accepted.connect(process_result)

    def list_diff_result(self, result):
        self._set_status('')
        if result['returncode'] == 0:
            archive_newer = ArchiveModel.get(name=result['params']['archive_name_newer'])
            archive_older = ArchiveModel.get(name=result['params']['archive_name_older'])
            window = DiffResult(result['data'], archive_newer, archive_older, result['params']['json_lines'])
            self._toggle_all_buttons(True)
            window.setParent(self, QtCore.Qt.Sheet)
            self._resultwindow = window  # for testing
            window.show()

    def rename_action(self):
        profile = self.profile()
        params = BorgRenameThread.prepare(profile)
        if not params['ok']:
            self._set_status(params['message'])
            return

        archive_name = self.selected_archive_name()
        if archive_name is not None:
            new_name, finished = QInputDialog.getText(
                self,
                self.tr("Change name"),
                self.tr("New archive name:"),
                text=archive_name)

            if not finished:
                return

            if not new_name:
                self._set_status(self.tr('Archive name cannot be blank.'))
                return

            new_name_exists = ArchiveModel.get_or_none(name=new_name, repo=profile.repo)
            if new_name_exists is not None:
                self._set_status(self.tr('An archive with this name already exists.'))
                return

            params['cmd'][-1] += f'::{archive_name}'
            params['cmd'].append(new_name)

            thread = BorgRenameThread(params['cmd'], params, parent=self)
            thread.updated.connect(self._set_status)
            thread.result.connect(self.rename_result)
            self._toggle_all_buttons(False)
            thread.start()
        else:
            self._set_status(self.tr("No archive selected"))

    def rename_result(self, result):
        if result['returncode'] == 0:
            self._set_status(self.tr('Archive renamed.'))
            self.populate_from_profile()
        else:
            self._toggle_all_buttons(True)
