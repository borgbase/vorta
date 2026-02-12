import logging

from PyQt6 import QtWidgets, uic
from PyQt6.QtWidgets import QDialog, QFileDialog

from vorta.borg.export_tar import BorgExportTar
from vorta.utils import get_asset

uifile = get_asset("UI/export_tar_dialog.ui")
ExportTarDialogUI, ExportTarDialogBase = uic.loadUiType(uifile)

logger = logging.getLogger(__name__)


class ExportTarDialog(ExportTarDialogBase, ExportTarDialogUI):
    def __init__(self, parent=None, profile=None, archive_name=None):
        super().__init__(parent)
        self.setupUi(self)
        self.profile = profile
        self.archive_name = archive_name
        self.main_window = parent

        self.archiveNameLabel.setText(self.archive_name)

        # Connect signals
        self.btnBrowse.clicked.connect(self.choose_destination)
        self.buttonBox.accepted.connect(self.start_export)

        # Defaults
        self.comboCompression.setCurrentIndex(0)  # none

    def choose_destination(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save Tarball"),
            f"{self.archive_name}.tar",
            self.tr("Tar Archives (*.tar *.tar.gz *.tar.lz4 *.tar.zstd *.tar.xz)"),
        )
        if filename:
            self.destinationInput.setText(filename)

            # Auto-detect compression from extension
            if filename.endswith('.tar.gz'):
                self.set_compression('gzip')
            elif filename.endswith('.tar.lz4'):
                self.set_compression('lz4')
            elif filename.endswith('.tar.zstd'):
                self.set_compression('zstd')
            elif filename.endswith('.tar.xz'):
                self.set_compression('xz')
            elif filename.endswith('.tar'):
                self.set_compression('none')

    def set_compression(self, name):
        index = self.comboCompression.findText(name)
        if index >= 0:
            self.comboCompression.setCurrentIndex(index)

    def start_export(self):
        destination = self.destinationInput.text()
        if not destination:
            # Maybe show a warning?
            return

        compression = self.comboCompression.currentText()
        strip_components = self.spinStripComponents.value()

        job_data = BorgExportTar.prepare(self.profile, self.archive_name, destination, compression, strip_components)

        if job_data['ok']:
            job = BorgExportTar(job_data['cmd'], job_data, site=self.profile.repo.id)
            # We need to add the job to the job manager, not just start it,
            # usually `app.jobs_manager.add_job(job)`
            # The parent (ArchiveTab) usually handles this, or we can access via app.

            if self.main_window and hasattr(self.main_window, 'app'):
                self.main_window.app.jobs_manager.add_job(job)
            else:
                # Fallback if accessed differently
                job.start()
