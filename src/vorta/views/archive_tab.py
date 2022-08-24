import logging
import os.path
import sys
from datetime import timedelta
from typing import Dict, Optional
from PyQt5 import QtCore, uic
from PyQt5.QtCore import QItemSelectionModel, QMimeData, QPoint, Qt, pyqtSlot
from PyQt5.QtGui import QDesktopServices, QKeySequence
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QHeaderView,
    QInputDialog,
    QLayout,
    QMenu,
    QMessageBox,
    QShortcut,
    QTableView,
    QTableWidgetItem,
    QWidget,
)
from vorta.borg.check import BorgCheckJob
from vorta.borg.compact import BorgCompactJob
from vorta.borg.delete import BorgDeleteJob
from vorta.borg.diff import BorgDiffJob
from vorta.borg.extract import BorgExtractJob
from vorta.borg.info_archive import BorgInfoArchiveJob
from vorta.borg.list_archive import BorgListArchiveJob
from vorta.borg.list_repo import BorgListRepoJob
from vorta.borg.mount import BorgMountJob
from vorta.borg.prune import BorgPruneJob
from vorta.borg.rename import BorgRenameJob
from vorta.borg.umount import BorgUmountJob
from vorta.store.models import ArchiveModel, BackupProfileMixin
from vorta.utils import choose_file_dialog, format_archive_name, get_asset, get_mount_points, pretty_bytes
from vorta.views import diff_result, extract_dialog
from vorta.views.diff_result import DiffResultDialog, DiffTree
from vorta.views.extract_dialog import ExtractDialog, ExtractTree
from vorta.views.source_tab import SizeItem
from vorta.views.utils import get_colored_icon

uifile = get_asset('UI/archivetab.ui')
ArchiveTabUI, ArchiveTabBase = uic.loadUiType(uifile)

logger = logging.getLogger(__name__)


class ArchiveTab(ArchiveTabBase, ArchiveTabUI, BackupProfileMixin):
    prune_intervals = ['hour', 'day', 'week', 'month', 'year']

    def __init__(self, parent=None, app=None):
        """Init."""
        super().__init__(parent)
        self.setupUi(parent)
        self.mount_points = {}  # mount points of archives
        self.repo_mount_point: Optional[str] = None  # mount point of whole repo
        self.menu = None
        self.app = app
        self.toolBox.setCurrentIndex(0)
        self.repoactions_enabled = True

        #: Tooltip dict to save the tooltips set in the designer
        self.tooltip_dict: Dict[QWidget, str] = {}
        self.tooltip_dict[self.bDiff] = self.bDiff.toolTip()
        self.tooltip_dict[self.bDelete] = self.bDelete.toolTip()

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
        self.archiveTable.setEditTriggers(QTableView.NoEditTriggers)
        self.archiveTable.setWordWrap(False)
        self.archiveTable.setTextElideMode(QtCore.Qt.ElideLeft)
        self.archiveTable.setAlternatingRowColors(True)
        self.archiveTable.cellDoubleClicked.connect(self.cell_double_clicked)
        self.archiveTable.setSortingEnabled(True)
        self.archiveTable.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.archiveTable.customContextMenuRequested.connect(self.archiveitem_contextmenu)

        # shortcuts
        shortcut_copy = QShortcut(QKeySequence.StandardKey.Copy, self.archiveTable)
        shortcut_copy.activated.connect(self.archive_copy)

        # single and double selection feature
        self.archiveTable.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self.archiveTable.selectionModel().selectionChanged.connect(self.on_selection_change)

        # connect archive actions
        self.bMountArchive.clicked.connect(self.bmountarchive_clicked)
        self.bRefreshArchive.clicked.connect(self.refresh_archive_info)
        self.bRename.clicked.connect(self.rename_action)
        self.bDelete.clicked.connect(self.delete_action)
        self.bExtract.clicked.connect(self.extract_action)
        self.compactButton.clicked.connect(self.compact_action)

        # other signals
        self.bList.clicked.connect(self.refresh_archive_list)
        self.bPrune.clicked.connect(self.prune_action)
        self.bCheck.clicked.connect(self.check_action)
        self.bDiff.clicked.connect(self.diff_action)
        self.bMountRepo.clicked.connect(self.bmountrepo_clicked)

        self.archiveNameTemplate.textChanged.connect(
            lambda tpl, key='new_archive_name': self.save_archive_template(tpl, key)
        )
        self.prunePrefixTemplate.textChanged.connect(
            lambda tpl, key='prune_prefix': self.save_archive_template(tpl, key)
        )

        self.populate_from_profile()
        self.selected_archives = None  # TODO: remove unused variable
        self.set_icons()

        # Connect to palette change
        self.app.paletteChanged.connect(lambda p: self.set_icons())

    def set_icons(self):
        "Used when changing between light- and dark mode"
        self.bCheck.setIcon(get_colored_icon('check-circle'))
        self.bDiff.setIcon(get_colored_icon('stream-solid'))
        self.bPrune.setIcon(get_colored_icon('cut'))
        self.bList.setIcon(get_colored_icon('refresh'))
        self.compactButton.setIcon(get_colored_icon('broom-solid'))
        self.toolBox.setItemIcon(0, get_colored_icon('tasks'))
        self.toolBox.setItemIcon(1, get_colored_icon('cut'))
        self.bRefreshArchive.setIcon(get_colored_icon('refresh'))
        self.bRename.setIcon(get_colored_icon('edit'))
        self.bDelete.setIcon(get_colored_icon('trash'))
        self.bExtract.setIcon(get_colored_icon('cloud-download'))

        self.bmountarchive_refresh(icon_only=True)
        self.bmountrepo_refresh()

    @pyqtSlot(QPoint)
    def archiveitem_contextmenu(self, pos: QPoint):
        # index under cursor
        index = self.archiveTable.indexAt(pos)
        if not index.isValid():
            return  # popup only for items

        selected_rows = self.archiveTable.selectionModel().selectedRows(index.column())

        if selected_rows and index not in selected_rows:
            return  # popup only for selected items

        menu = QMenu(self.archiveTable)
        menu.addAction(
            get_colored_icon('copy'),
            self.tr("Copy"),
            lambda: self.archive_copy(index=index),
        )
        menu.addSeparator()

        # archive actions
        archive_actions = []
        archive_actions.append(
            menu.addAction(
                self.bRefreshArchive.icon(),
                self.bRefreshArchive.text(),
                self.refresh_archive_info,
            )
        )
        archive_actions.append(
            menu.addAction(
                self.bMountArchive.icon(),
                self.bMountArchive.text(),
                self.bmountarchive_clicked,
            )
        )
        archive_actions.append(menu.addAction(self.bExtract.icon(), self.bExtract.text(), self.extract_action))
        archive_actions.append(menu.addAction(self.bRename.icon(), self.bRename.text(), self.rename_action))
        # deletion possible with one but also multiple archives
        menu.addAction(self.bDelete.icon(), self.bDelete.text(), self.delete_action)

        if not (self.repoactions_enabled and len(selected_rows) <= 1):
            for action in archive_actions:
                action.setEnabled(False)

        # diff action
        menu.addSeparator()
        diff_action = QAction(self.bDiff.icon(), self.bDiff.text(), menu)
        diff_action.triggered.connect(self.diff_action)
        menu.addAction(diff_action)

        selected_rows = self.archiveTable.selectionModel().selectedRows(index.column())
        diff_action.setEnabled(self.repoactions_enabled and len(selected_rows) == 2)

        menu.popup(self.archiveTable.viewport().mapToGlobal(pos))

    def cancel_action(self):
        self._set_status(self.tr("Action cancelled."))
        self._toggle_all_buttons(True)

    def _set_status(self, text):
        self.mountErrors.setText(text)
        self.mountErrors.repaint()

    def _toggle_all_buttons(self, enabled=True):
        """
        Set all the buttons in the archive panel to the given state.

        Parameters
        ----------
        enabled : bool, optional
            The enabled state, by default True
        """
        self.repoactions_enabled = enabled

        for button in [
            self.bCheck,
            self.bList,
            self.bPrune,
            self.bDiff,
            self.fArchiveActions,
            self.bMountRepo,
        ]:
            button.setEnabled(enabled)
            button.repaint()

        # Restore states
        self.on_selection_change()

    def populate_from_profile(self):
        """Populate archive list and prune settings from profile."""
        profile = self.profile()
        if profile.repo is not None:
            # get mount points
            self.mount_points, repo_mount_points = get_mount_points(profile.repo.url)
            if repo_mount_points:
                self.repo_mount_point = repo_mount_points[0]

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

            self.archiveTable.selectionModel().clearSelection()
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

    def on_selection_change(self, selected=None, deselected=None):
        """
        React to a change of the selection of the archiveTableView.

        Enables or disables archive actions and the diff button.
        Makes sure at maximum 2 rows are selected.

        Parameters
        ----------
        selected : QItemSelection, optional
            The new selection.
        deselected : QItemSelection, optional
            The previous selection.
        """
        # handle selection of more than 2 rows
        selectionModel: QItemSelectionModel = self.archiveTable.selectionModel()
        indexes = selectionModel.selectedRows()

        # Toggle archive actions frame
        layout: QLayout = self.fArchiveActions.layout()

        # toggle delete button
        if len(indexes) > 0:
            self.bDelete.setEnabled(True)
            self.bDelete.setToolTip(self.tooltip_dict.get(self.bDelete, ""))
        else:
            self.bDelete.setEnabled(False)
            tooltip = self.tooltip_dict[self.bDelete]
            self.bDelete.setToolTip(tooltip + " " + self.tr("(Select minimum one archive)"))

        # Toggle diff button
        if len(indexes) == 2:
            # Enable diff button
            self.bDiff.setEnabled(True)
            self.bDiff.setToolTip(self.tooltip_dict.get(self.bDiff, ""))
        else:
            # disable diff button
            self.bDiff.setEnabled(False)

            tooltip = self.tooltip_dict[self.bDiff]
            self.bDiff.setToolTip(tooltip + " " + self.tr("(Select two archives)"))

        if len(indexes) == 1:
            # Enable archive actions
            self.fArchiveActions.setEnabled(True)

            for index in range(layout.count()):
                widget = layout.itemAt(index).widget()
                widget.setToolTip(self.tooltip_dict.get(widget, ""))

            # refresh bMountArchive for the selected archive
            self.bmountarchive_refresh()
        else:
            # too few or too many selected.
            self.fArchiveActions.setEnabled(False)

            for index in range(layout.count()):
                widget = layout.itemAt(index).widget()
                tooltip = widget.toolTip()

                tooltip = self.tooltip_dict.setdefault(widget, tooltip)
                widget.setToolTip(tooltip + " " + self.tr("(Select exactly one archive)"))

            # special treatment for dynamic mount/unmount button.
            self.bmountarchive_refresh()
            tooltip = self.bMountArchive.toolTip()
            self.bMountArchive.setToolTip(tooltip + " " + self.tr("(Select exactly one archive)"))

    def archive_copy(self, index=None):
        """
        Copy an archive name to the clipboard.

        Copies the first selected archive if no index is specified.
        """
        if index is None:
            indexes = self.archiveTable.selectionModel().selectedRows()

            if not indexes:
                return

            index = indexes[0]

        archive_name = self.archiveTable.item(index.row(), 4).text()

        data = QMimeData()
        data.setText(archive_name)

        QApplication.clipboard().setMimeData(data)

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
        params = BorgCheckJob.prepare(self.profile())
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

        job = BorgCheckJob(params['cmd'], params, self.profile().repo.id)
        job.updated.connect(self._set_status)
        job.result.connect(self.check_result)
        self._toggle_all_buttons(False)
        self.app.jobs_manager.add_job(job)

    def check_result(self, result):
        if result['returncode'] == 0:
            self._toggle_all_buttons(True)

    def compact_action(self):
        params = BorgCompactJob.prepare(self.profile())
        if params['ok']:
            job = BorgCompactJob(params['cmd'], params, self.profile().repo.id)
            job.updated.connect(self._set_status)
            job.result.connect(self.compact_result)
            self._toggle_all_buttons(False)
            self.app.jobs_manager.add_job(job)
        else:
            self._set_status(params['message'])

    def compact_result(self, result):
        self._toggle_all_buttons(True)

    def prune_action(self):
        params = BorgPruneJob.prepare(self.profile())
        if params['ok']:
            job = BorgPruneJob(params['cmd'], params, self.profile().repo.id)
            job.updated.connect(self._set_status)
            job.result.connect(self.prune_result)
            self._toggle_all_buttons(False)
            self.app.jobs_manager.add_job(job)
        else:
            self._set_status(params['message'])

    def prune_result(self, result):
        if result['returncode'] == 0:
            self._set_status(self.tr('Pruning finished.'))
            self.refresh_archive_list()
        else:
            self._toggle_all_buttons(True)

    def refresh_archive_list(self):
        params = BorgListRepoJob.prepare(self.profile())
        if params['ok']:
            job = BorgListRepoJob(params['cmd'], params, self.profile().repo.id)
            job.updated.connect(self._set_status)
            job.result.connect(self.list_result)
            self._toggle_all_buttons(False)
            self.app.jobs_manager.add_job(job)
        else:
            self._set_status(params['message'])

    def list_result(self, result):
        self._toggle_all_buttons(True)
        if result['returncode'] == 0:
            self._set_status(self.tr('Refreshed archives.'))
            self.populate_from_profile()

    def refresh_archive_info(self):
        archive_name = self.selected_archive_name()
        if archive_name is not None:
            params = BorgInfoArchiveJob.prepare(self.profile(), archive_name)
            if params['ok']:
                job = BorgInfoArchiveJob(params['cmd'], params, self.profile().repo.id)
                job.updated.connect(self._set_status)
                job.result.connect(self.info_result)
                self._toggle_all_buttons(False)
                self.app.jobs_manager.add_job(job)

    def info_result(self, result):
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

    def bmountarchive_clicked(self):
        """
        Handle `bMountArchive` being clicked.

        Mount or umount the current archive depending on its current state.
        """
        archive_name = self.selected_archive_name()

        if not archive_name:
            logger.warning("Archive name of selection is empty.")
            return

        if archive_name in self.mount_points:
            self.unmount_action(archive_name=archive_name)
        else:
            self.mount_action(archive_name=archive_name)

    def bmountrepo_clicked(self):
        """
        Handle `bMountRepo` being clicked.

        Mount or umount the repository depending on its current state.
        """
        if self.repo_mount_point:
            self.unmount_action()
        else:
            self.mount_action()

    def bmountarchive_refresh(self, icon_only=False):
        """
        Update label, tooltip and state of `bMountArchive`.

        The new state depends on the mount status of the current archive.
        This also updates the icon of the button.
        """
        archive_name = self.selected_archive_name()

        if archive_name in self.mount_points:
            self.bMountArchive.setIcon(get_colored_icon('eject'))
            if not icon_only:
                self.bMountArchive.setText(self.tr("Unmount"))
                self.bMountArchive.setToolTip(self.tr('Unmount the selected archive from the file system'))
        else:
            self.bMountArchive.setIcon(get_colored_icon('folder-open'))
            if not icon_only:
                self.bMountArchive.setText(self.tr("Mount…"))
                self.bMountArchive.setToolTip(self.tr("Mount the selected archive " + "as a folder in the file system"))

    def bmountrepo_refresh(self):
        """
        Update label, tooltip and state of `bMountRepo`.

        The new state depends on the mount status of the current archive.
        This also updates the icon of the button.
        """
        if self.repo_mount_point:
            self.bMountRepo.setText(self.tr("Unmount"))
            self.bMountRepo.setToolTip(self.tr('Unmount the repository from the file system'))
            self.bMountRepo.setIcon(get_colored_icon('eject'))
        else:
            self.bMountRepo.setText(self.tr("Mount…"))
            self.bMountRepo.setIcon(get_colored_icon('folder-open'))
            self.bMountRepo.setToolTip(self.tr("Mount the repository as a folder in the file system"))

    def mount_action(self, archive_name=None):
        """
        Mount an archive or the whole repository.

        Opens a file chooser to let the user choose a mount point and starts
        the borg job for mounting afterwards.

        Parameters
        ----------
        archive_name : str, optional
            The archive to mount or None, by default None
        """
        profile = self.profile()
        params = BorgMountJob.prepare(profile)
        if not params['ok']:
            self._set_status(params['message'])
            return

        if archive_name:
            # mount archive
            params['cmd'][-1] += f'::{archive_name}'
            params['current_archive'] = archive_name
        # else mount complete repo

        def receive():
            mount_point = dialog.selectedFiles()
            if mount_point:
                params['cmd'].append(mount_point[0])
                params['mount_point'] = mount_point[0]

                if params['ok']:
                    self._toggle_all_buttons(False)
                    job = BorgMountJob(params['cmd'], params, self.profile().repo.id)
                    job.updated.connect(self.mountErrors.setText)
                    job.result.connect(self.mount_result)
                    self.app.jobs_manager.add_job(job)

        dialog = choose_file_dialog(self, self.tr("Choose Mount Point"), want_folder=True)
        dialog.open(receive)

    def mount_result(self, result):
        if result['returncode'] == 0:
            self._set_status(self.tr('Mounted successfully.'))

            mount_point = result['params']['mount_point']

            if result['params'].get('current_archive'):
                # archive was mounted
                archive_name = result['params']['current_archive']
                self.mount_points[archive_name] = mount_point

                # update column in table
                archive_name = result['params']['current_archive']
                row = self.row_of_archive(archive_name)
                item = QTableWidgetItem(result['cmd'][-1])
                self.archiveTable.setItem(row, 3, item)

                # update button
                self.bmountarchive_refresh()
            else:
                # whole repo was mounted
                self.repo_mount_point = mount_point
                self.bmountrepo_refresh()

        self._toggle_all_buttons(True)

    def unmount_action(self, archive_name=None):
        """
        Unmount a (mounted) repository or archive.

        If the target isn't mounted nothing happens.

        Parameters
        ----------
        archive_name : str, optional
            The archive to unmount, by default None
        """
        if archive_name:
            # unmount a single archive
            mount_point = self.mount_points.get(archive_name)
        else:
            # unmount the whole repository
            mount_point = self.repo_mount_point

        if mount_point is not None:
            profile = self.profile()
            params = BorgUmountJob.prepare(profile)
            if not params['ok']:
                self._set_status(params['message'])
                return

            if archive_name:
                params['current_archive'] = archive_name
            params['mount_point'] = mount_point

            if os.path.normpath(mount_point) in params['active_mount_points']:
                params['cmd'].append(mount_point)

                job = BorgUmountJob(params['cmd'], params, self.profile().repo.id)
                job.updated.connect(self.mountErrors.setText)
                job.result.connect(self.umount_result)
                self.app.jobs_manager.add_job(job)
            else:
                self._set_status(self.tr('Mount point not active.'))
                return

    def umount_result(self, result):
        self._toggle_all_buttons(True)
        archive_name = result['params'].get('current_archive')
        mount_point = result['params']['mount_point']

        if result['returncode'] == 0:
            self._set_status(self.tr('Un-mounted successfully.'))

            if archive_name:
                # unmount single archive
                del self.mount_points[archive_name]
                row = self.row_of_archive(archive_name)
                item = QTableWidgetItem('')
                self.archiveTable.setItem(row, 3, item)

                # update button
                self.bmountarchive_refresh()
            else:
                # unmount repo
                self.repo_mount_point = None

                self.bmountrepo_refresh()
        else:
            self._set_status(self.tr('Unmounting failed. Make sure no programs are using {}').format(mount_point))

    def save_prune_setting(self, new_value=None):
        profile = self.profile()
        for i in self.prune_intervals:
            setattr(profile, f'prune_{i}', getattr(self, f'prune_{i}').value())
        profile.prune_keep_within = self.prune_keep_within.text()
        profile.save()

    def extract_action(self):
        """
        Open a dialog for choosing what to extract from the selected archive.
        """
        profile = self.profile()

        row_selected = self.archiveTable.selectionModel().selectedRows()
        if row_selected:
            archive_cell = self.archiveTable.item(row_selected[0].row(), 4)
            if archive_cell:
                archive_name = archive_cell.text()
                params = BorgListArchiveJob.prepare(profile, archive_name)

                if not params['ok']:
                    self._set_status(params['message'])
                    return
                self._set_status('')
                self._toggle_all_buttons(False)

                job = BorgListArchiveJob(params['cmd'], params, self.profile().repo.id)
                job.updated.connect(self.mountErrors.setText)
                job.result.connect(self.extract_list_result)
                self.app.jobs_manager.add_job(job)
                return job
        else:
            self._set_status(self.tr('Select an archive to restore first.'))

    def extract_list_result(self, result):
        """Process the contents of the archive to extract."""
        self._set_status('')
        if result['returncode'] == 0:
            archive = ArchiveModel.get(name=result['params']['archive_name'])
            model = ExtractTree()
            self._set_status(self.tr("Processing archive contents"))
            self._t = extract_dialog.ParseThread(result['data'], model)
            self._t.finished.connect(lambda: self.extract_show_dialog(archive, model))
            self._t.start()

    def extract_show_dialog(self, archive, model):
        """Show the dialog for choosing the archive contents to extract."""
        self._set_status('')

        def process_result():
            def receive():
                extraction_folder = dialog.selectedFiles()
                if extraction_folder:
                    params = BorgExtractJob.prepare(self.profile(), archive.name, model, extraction_folder[0])
                    if params['ok']:
                        self._toggle_all_buttons(False)
                        job = BorgExtractJob(params['cmd'], params, self.profile().repo.id)
                        job.updated.connect(self.mountErrors.setText)
                        job.result.connect(self.extract_archive_result)
                        self.app.jobs_manager.add_job(job)
                    else:
                        self._set_status(params['message'])

            dialog = choose_file_dialog(self, self.tr("Choose Extraction Point"), want_folder=True)
            dialog.open(receive)

        window = ExtractDialog(archive, model)
        self._toggle_all_buttons(True)
        window.setParent(self, QtCore.Qt.Sheet)
        self._window = window  # for testing
        window.show()
        window.accepted.connect(process_result)

    def extract_archive_result(self, result):
        """Finished extraction."""
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
        # Since this function modify the UI, we can't put the whole function in a JobQUeue.

        # determine selected archives
        archives = []
        for index in self.archiveTable.selectionModel().selectedRows():
            archive_cell = self.archiveTable.item(index.row(), 4)
            if archive_cell:
                archives.append(archive_cell.text())

        if not archives:
            self._set_status(self.tr("No archive selected"))
            return

        params = BorgDeleteJob.prepare(self.profile(), archives)
        if not params['ok']:
            self._set_status(params['message'])
            return

        if len(archives) > 1:
            body = self.tr("Are you sure you want to delete all the selected archives?")
        else:
            body = self.tr("Are you sure you want to delete the selected archive?")
        if not self.confirm_dialog(self.tr("Confirm deletion"), body):
            return

        job = BorgDeleteJob(params['cmd'], params, self.profile().repo.id)
        job.updated.connect(self._set_status)
        job.result.connect(self.delete_result)
        self._toggle_all_buttons(False)
        self.app.jobs_manager.add_job(job)

    def delete_result(self, result):
        archives = result['params']['archives']
        if result['returncode'] == 0:
            if len(archives) > 1:
                status = self.tr('Archives deleted.')
            else:
                status = self.tr('Archive deleted.')
            self._set_status(status)

            # remove rows from list and database
            for archive in archives:
                for entry in self.archiveTable.findItems(archive, QtCore.Qt.MatchExactly):
                    self.archiveTable.removeRow(entry.row())
                ArchiveModel.get(name=archive).delete_instance()

        self._toggle_all_buttons(True)

    def diff_action(self):
        """
        Handle the diff button being clicked.

        Exactly two archives must be selected in `archiveTable`. This is
        usually enforced by `on_selection_change`.
        """
        selected_archives = self.archiveTable.selectionModel().selectedRows()
        profile = self.profile()

        name1 = self.archiveTable.item(selected_archives[0].row(), 4).text()
        name2 = self.archiveTable.item(selected_archives[1].row(), 4).text()

        archive1, archive2 = (
            profile.repo.archives.select()
            .where((ArchiveModel.name == name1) | (ArchiveModel.name == name2))
            .order_by(ArchiveModel.time.desc())
        )

        archive_name_newer = archive1.name
        archive_name_older = archive2.name

        # Start diff job
        params = BorgDiffJob.prepare(profile, archive_name_older, archive_name_newer)

        if params['ok']:
            self._toggle_all_buttons(False)
            job = BorgDiffJob(params['cmd'], params, self.profile().repo.id)
            job.updated.connect(self.mountErrors.setText)
            job.result.connect(self.list_diff_result)
            self.app.jobs_manager.add_job(job)
        else:
            self._set_status(params['message'])

    def list_diff_result(self, result):
        """
        Process the result of the `BorgDiffJob`.

        The `BorgDiffJob` was initiated by `diff_action`.

        Parameters
        ----------
        result : dict
            The BorgJob result.
        """
        self._set_status('')
        if result['returncode'] == 0:
            archive_newer = ArchiveModel.get(name=result['params']['archive_name_newer'])
            archive_older = ArchiveModel.get(name=result['params']['archive_name_older'])
            self._set_status(self.tr("Processing diff results."))

            model = DiffTree()

            self._t = diff_result.ParseThread(result['data'], result['params']['json_lines'], model)
            self._t.finished.connect(lambda: self.show_diff_result(archive_newer, archive_older, model))
            self._t.start()

    def show_diff_result(self, archive_newer, archive_older, model):
        self._t = None

        # show dialog
        self._toggle_all_buttons(True)
        self._set_status('')
        window = DiffResultDialog(archive_newer, archive_older, model)
        window.setParent(self)
        window.setWindowFlags(Qt.WindowType.Window)
        window.setWindowModality(Qt.WindowModality.NonModal)
        self._resultwindow = window  # for testing
        window.show()

    def rename_action(self):
        profile = self.profile()
        params = BorgRenameJob.prepare(profile)
        if not params['ok']:
            self._set_status(params['message'])
            return

        archive_name = self.selected_archive_name()
        if archive_name is not None:
            new_name, finished = QInputDialog.getText(
                self,
                self.tr("Change name"),
                self.tr("New archive name:"),
                text=archive_name,
            )

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
            job = BorgRenameJob(params['cmd'], params, self.profile().repo.id)
            job.updated.connect(self._set_status)
            job.result.connect(self.rename_result)
            self._toggle_all_buttons(False)
            self.app.jobs_manager.add_job(job)
        else:
            self._set_status(self.tr("No archive selected"))

    def rename_result(self, result):
        if result['returncode'] == 0:
            self._set_status(self.tr('Archive renamed.'))
            self.populate_from_profile()
        else:
            self._toggle_all_buttons(True)
