from vorta.borg.delete import BorgDeleteJob
from vorta.store.models import ArchiveModel


class ArchiveDelete:
    def __init__(self, tab):
        self.tab = tab

    def delete_action(self):
        # Since this function modifies the UI, we can't put the whole function in a JobQueue.
        archives = [archive.name for archive in self.tab.selected_archives()]

        if not archives:
            self.tab._set_status(self.tab.tr("No archive selected"))
            return

        params = BorgDeleteJob.prepare(self.tab.profile(), archives)
        if not params['ok']:
            self.tab._set_status(params['message'])
            return

        if len(archives) > 1:
            body = self.tab.tr("Are you sure you want to delete all the selected archives?")
        else:
            body = self.tab.tr("Are you sure you want to delete the selected archive?")
        if not self.tab.confirm_dialog(self.tab.tr("Confirm deletion"), body):
            return

        job = BorgDeleteJob(params['cmd'], params, self.tab.profile().repo.id)
        job.updated.connect(self.tab._set_status)
        job.result.connect(self.delete_result)
        self.tab._toggle_all_buttons(False)
        self.tab.app.jobs_manager.add_job(job)

    def delete_result(self, result):
        archives = result['params']['archives']
        if result['returncode'] == 0:
            if len(archives) > 1:
                status = self.tab.tr('Archives deleted.')
            else:
                status = self.tab.tr('Archive deleted.')
            self.tab._set_status(status)

            repo = self.tab.profile().repo
            for archive in archives:
                archive_obj = ArchiveModel.get_or_none(name=archive, repo=repo)
                if archive_obj:
                    archive_obj.delete_instance()
            self.tab.populate_from_profile(preserve_view=True)

        self.tab._toggle_all_buttons(True)
