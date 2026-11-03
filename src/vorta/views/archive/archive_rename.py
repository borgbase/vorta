from PyQt6 import QtCore
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDesktopServices

from vorta.borg.rename import BorgRenameJob
from vorta.store.models import ArchiveModel
from vorta.views.partials.archive_table_model import ArchiveTableModel


class ArchiveRename:
    def __init__(self, tab):
        self.tab = tab

    def cell_double_clicked(self, index=None):
        """Open a mounted archive's folder, or start an in-place rename."""
        if isinstance(index, QtCore.QModelIndex) and index.isValid():
            column = index.column()
        else:
            index = self.tab.archiveTable.currentIndex()
            column = ArchiveTableModel.COL_NAME

        if not index.isValid():
            return

        if column == ArchiveTableModel.COL_MOUNT:
            archive = index.data(ArchiveTableModel.ArchiveRole)
            mount_point = self.tab.mount_points.get(archive.name) if archive else None
            if mount_point is not None:
                QDesktopServices.openUrl(QtCore.QUrl(f'file:///{mount_point}'))
            return

        if column == ArchiveTableModel.COL_NAME:
            if not self.tab.bRename.isEnabled():
                return
            archive = index.data(ArchiveTableModel.ArchiveRole)
            if archive is None:
                return
            self.tab.renamed_archive_original_name = archive.name
            self.tab.is_editing = True
            self.tab.archiveTable.edit(index.siblingAtColumn(ArchiveTableModel.COL_NAME))

    def on_name_edited(self, top_left, bottom_right, roles=None):
        """Handle a committed in-place name edit (model `dataChanged` from the Name column)."""
        if not self.tab.is_editing or top_left.column() != ArchiveTableModel.COL_NAME:
            return
        self.tab.is_editing = False

        archive = top_left.data(ArchiveTableModel.ArchiveRole)
        original = self.tab.renamed_archive_original_name
        new_name = archive.name if archive else ''
        profile = self.tab.profile()

        if new_name == original:
            return

        if not new_name:
            self._revert_name(top_left, original)
            self.tab._set_status(self.tab.tr('Archive name cannot be blank.'))
            return

        if ArchiveModel.get_or_none(name=new_name, repo=profile.repo) is not None:
            self.tab._set_status(self.tab.tr('An archive with this name already exists.'))
            self._revert_name(top_left, original)
            return

        params = BorgRenameJob.prepare(profile, original, new_name)
        if not params['ok']:
            self.tab._set_status(params['message'])
            self._revert_name(top_left, original)
            return

        self.tab._set_status(self.tab.tr('Renaming archive...'))
        job = BorgRenameJob(params['cmd'], params, profile.repo.id)
        job.updated.connect(self.tab._set_status)
        job.result.connect(self.rename_result)
        self.tab._toggle_all_buttons(False)
        self.tab.app.jobs_manager.add_job(job)

    def _revert_name(self, index, original):
        """Restore the model's name after a rejected edit."""
        self.tab.archive_model.setData(index, original, Qt.ItemDataRole.EditRole)

    def rename_result(self, result):
        if result['returncode'] == 0:
            self.tab.refresh_archive_info()
            self.tab._set_status(self.tab.tr('Archive renamed.'))
            self.tab.renamed_archive_original_name = None
            self.tab.populate_from_profile()
        else:
            # rename failed: refresh from the DB to drop the optimistically-applied name
            self.tab.renamed_archive_original_name = None
            self.tab.populate_from_profile(preserve_view=True)
