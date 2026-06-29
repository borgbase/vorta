from PyQt6.QtCore import Qt

from vorta.borg.diff import BorgDiffJob
from vorta.store.models import ArchiveModel
from vorta.views.dialogs.archive import diff_result
from vorta.views.dialogs.archive.diff_result import DiffResultDialog, DiffTree


class ArchiveDiff:
    def __init__(self, tab):
        self.tab = tab

    def diff_action(self):
        """
        Handle the diff button being clicked.

        Exactly two archives must be selected in `archiveTable`. This is
        usually enforced by `on_selection_change`.
        """
        archives = self.tab.selected_archives()
        profile = self.tab.profile()

        name1 = archives[0].name
        name2 = archives[1].name

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
            self.tab._toggle_all_buttons(False)
            job = BorgDiffJob(params['cmd'], params, self.tab.profile().repo.id)
            job.updated.connect(self.tab.mountErrors.setText)
            job.result.connect(self.list_diff_result)
            self.tab.app.jobs_manager.add_job(job)
        else:
            self.tab._set_status(params['message'])

    def list_diff_result(self, result):
        """
        Process the result of the `BorgDiffJob`.

        The `BorgDiffJob` was initiated by `diff_action`.

        Parameters
        ----------
        result : dict
            The BorgJob result.
        """
        self.tab._set_status('')
        if result['returncode'] == 0:
            archive_newer = ArchiveModel.get(name=result['params']['archive_name_newer'])
            archive_older = ArchiveModel.get(name=result['params']['archive_name_older'])
            self.tab._set_status(self.tab.tr("Processing diff results."))

            model = DiffTree()

            self.tab._t = diff_result.ParseThread(result['data'], result['params']['json_lines'], model)
            self.tab._t.finished.connect(lambda: self.show_diff_result(archive_newer, archive_older, model))
            self.tab._t.start()

    def show_diff_result(self, archive_newer, archive_older, model):
        self.tab._t = None

        # show dialog
        self.tab._toggle_all_buttons(True)
        self.tab._set_status('')
        window = DiffResultDialog(archive_newer, archive_older, model)
        window.setParent(self.tab)
        window.setWindowFlags(Qt.WindowType.Window)
        window.setWindowModality(Qt.WindowModality.NonModal)
        self.tab._resultwindow = window  # for testing
        window.show()
