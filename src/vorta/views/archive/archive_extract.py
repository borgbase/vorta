from PyQt6 import QtCore

from vorta.borg.extract import BorgExtractJob
from vorta.borg.list_archive import BorgListArchiveJob
from vorta.store.models import ArchiveModel
from vorta.utils import choose_file_dialog
from vorta.views.dialogs.archive import extract as extract_dialog
from vorta.views.dialogs.archive.extract import ExtractDialog, ExtractTree


class ArchiveExtract:
    def __init__(self, tab):
        self.tab = tab

    def extract_action(self):
        """
        Open a dialog for choosing what to extract from the selected archive.
        """
        profile = self.tab.profile()

        row_selected = self.tab.archiveTable.selectionModel().selectedRows()
        if row_selected:
            archive_cell = self.tab.archiveTable.item(row_selected[0].row(), 4)
            if archive_cell:
                archive_name = archive_cell.text()
                params = BorgListArchiveJob.prepare(profile, archive_name)

                if not params['ok']:
                    self.tab._set_status(params['message'])
                    return
                self.tab._set_status('')
                self.tab._toggle_all_buttons(False)

                job = BorgListArchiveJob(params['cmd'], params, self.tab.profile().repo.id)
                job.updated.connect(self.tab.mountErrors.setText)
                job.result.connect(self.extract_list_result)
                self.tab.app.jobs_manager.add_job(job)
                return job
        else:
            self.tab._set_status(self.tab.tr('Select an archive to restore first.'))

    def extract_list_result(self, result):
        """Process the contents of the archive to extract."""
        self.tab._set_status('')
        if result['returncode'] == 0:
            archive = ArchiveModel.get(name=result['params']['archive_name'])
            model = ExtractTree()
            self.tab._set_status(self.tab.tr("Processing archive contents"))
            self.tab._t = extract_dialog.ParseThread(result['data'], model)
            self.tab._t.finished.connect(lambda: self.extract_show_dialog(archive, model))
            self.tab._t.start()

    def extract_show_dialog(self, archive, model):
        """Show the dialog for choosing the archive contents to extract."""
        self.tab._set_status('')

        def process_result():
            def receive():
                extraction_folder = dialog.selectedFiles()
                if extraction_folder:
                    params = BorgExtractJob.prepare(self.tab.profile(), archive.name, model, extraction_folder[0])
                    if params['ok']:
                        self.tab._toggle_all_buttons(False)
                        job = BorgExtractJob(params['cmd'], params, self.tab.profile().repo.id)
                        job.updated.connect(self.tab.mountErrors.setText)
                        job.result.connect(self.extract_archive_result)
                        self.tab.app.jobs_manager.add_job(job)
                    else:
                        self.tab._set_status(params['message'])

            dialog = choose_file_dialog(self.tab, self.tab.tr("Choose Extraction Point"), want_folder=True)
            dialog.open(receive)

        window = ExtractDialog(archive, model)
        self.tab._toggle_all_buttons(True)
        window.setParent(self.tab, QtCore.Qt.WindowType.Sheet)
        self.tab._window = window  # for testing
        window.show()
        window.accepted.connect(process_result)

    def extract_archive_result(self, result):
        """Finished extraction."""
        self.tab._toggle_all_buttons(True)
