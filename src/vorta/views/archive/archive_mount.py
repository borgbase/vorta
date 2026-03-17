import logging

from PyQt6.QtWidgets import QTableWidgetItem

from vorta.borg.mount import BorgMountJob
from vorta.borg.umount import BorgUmountJob
from vorta.i18n import translate
from vorta.utils import choose_file_dialog
from vorta.views.utils import get_colored_icon

logger = logging.getLogger(__name__)


class ArchiveMount:
    """Component handling the mount/unmount operations for the ArchiveTab."""

    def __init__(self, tab):
        self.tab = tab

    def bmountarchive_clicked(self):
        archive_name = self.tab.selected_archive_name()
        if not archive_name:
            logger.warning("Archive name of selection is empty.")
            return

        if archive_name in self.tab.mount_points:
            self.unmount_action(archive_name=archive_name)
        else:
            self.mount_action(archive_name=archive_name)

    def bmountrepo_clicked(self):
        if self.tab.repo_mount_point:
            self.unmount_action()
        else:
            self.mount_action()

    def bmountarchive_refresh(self, icon_only=False):
        archive_name = self.tab.selected_archive_name()

        if archive_name in self.tab.mount_points:
            self.tab.bMountArchive.setIcon(get_colored_icon('eject'))
            if not icon_only:
                self.tab.bMountArchive.setText(self.tab.tr("Unmount"))
                self.tab.bMountArchive.setToolTip(self.tab.tr('Unmount the selected archive from the file system'))
        else:
            self.tab.bMountArchive.setIcon(get_colored_icon('folder-open'))
            if not icon_only:
                self.tab.bMountArchive.setText(self.tab.tr("Mount…"))
                self.tab.bMountArchive.setToolTip(
                    self.tab.tr("Mount the selected archive as a folder in the file system")
                )

    def bmountrepo_refresh(self):
        if self.tab.repo_mount_point:
            self.tab.bMountRepo.setText(self.tab.tr("Unmount"))
            self.tab.bMountRepo.setToolTip(self.tab.tr('Unmount the repository from the file system'))
            self.tab.bMountRepo.setIcon(get_colored_icon('eject'))
        else:
            self.tab.bMountRepo.setText(self.tab.tr("Mount…"))
            self.tab.bMountRepo.setIcon(get_colored_icon('folder-open'))
            self.tab.bMountRepo.setToolTip(self.tab.tr("Mount the repository as a folder in the file system"))

    def mount_action(self, archive_name=None):
        profile = self.tab.profile()
        params = BorgMountJob.prepare(profile, archive=archive_name)
        if not params['ok']:
            self.tab._set_status(params['message'])
            return

        def receive():
            mount_point = dialog.selectedFiles()
            if mount_point:
                params['cmd'].append(mount_point[0])
                params['mount_point'] = mount_point[0]

                if params['ok']:
                    self.tab._toggle_all_buttons(False)
                    job = BorgMountJob(params['cmd'], params, self.tab.profile().repo.id)
                    job.updated.connect(self.tab.mountErrors.setText)
                    job.result.connect(self.mount_result)
                    self.tab.app.jobs_manager.add_job(job)

        dialog = choose_file_dialog(self.tab, self.tab.tr("Choose Mount Point"), want_folder=True)
        dialog.open(receive)

    def mount_result(self, result):
        if result['returncode'] == 0:
            self.tab._set_status(self.tab.tr('Mounted successfully.'))

            mount_point = result['params']['mount_point']

            if result['params'].get('mounted_archive'):
                archive_name = result['params']['mounted_archive']
                self.tab.mount_points[archive_name] = mount_point

                row = self.tab.row_of_archive(archive_name)
                item = QTableWidgetItem(result['cmd'][-1])
                self.tab.archiveTable.setItem(row, 3, item)

                self.bmountarchive_refresh()
            else:
                self.tab.repo_mount_point = mount_point
                self.bmountrepo_refresh()

        self.tab._toggle_all_buttons(True)

    def unmount_action(self, archive_name=None):
        if archive_name:
            mount_point = self.tab.mount_points.get(archive_name)
        else:
            mount_point = self.tab.repo_mount_point

        if mount_point is not None:
            profile = self.tab.profile()
            params = BorgUmountJob.prepare(profile, mount_point, archive_name=archive_name)
            if not params['ok']:
                self.tab._set_status(translate('message', params['message']))
                return

            job = BorgUmountJob(params['cmd'], params, self.tab.profile().repo.id)
            job.updated.connect(self.tab.mountErrors.setText)
            job.result.connect(self.umount_result)
            self.tab.app.jobs_manager.add_job(job)

    def umount_result(self, result):
        self.tab._toggle_all_buttons(True)
        archive_name = result['params'].get('current_archive')

        if result['returncode'] == 0:
            self.tab._set_status(self.tab.tr('Un-mounted successfully.'))

            if archive_name:
                del self.tab.mount_points[archive_name]
                row = self.tab.row_of_archive(archive_name)
                item = QTableWidgetItem('')
                self.tab.archiveTable.setItem(row, 3, item)
                self.bmountarchive_refresh()
            else:
                self.tab.repo_mount_point = None
                self.bmountrepo_refresh()
        else:
            self.tab._set_status(self.tab.tr('Error: Unmount failed. See log for details.'))
