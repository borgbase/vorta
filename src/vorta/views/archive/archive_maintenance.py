from vorta.borg.check import BorgCheckJob
from vorta.borg.compact import BorgCompactJob
from vorta.borg.prune import BorgPruneJob


class ArchiveMaintenance:
    def __init__(self, tab):
        self.tab = tab

    def check_action(self):
        params = BorgCheckJob.prepare(self.tab.profile())
        if not params['ok']:
            self.tab._set_status(params['message'])
            return

        # Conditions are met (borg binary available, etc)
        archives = self.tab.selected_archives()
        if archives:
            params['cmd'][-1] += f'::{archives[0].name}'

        job = BorgCheckJob(params['cmd'], params, self.tab.profile().repo.id)
        job.updated.connect(self.tab._set_status)
        job.result.connect(self.check_result)
        self.tab._toggle_all_buttons(False)
        self.tab.app.jobs_manager.add_job(job)

    def check_result(self, result):
        if result['returncode'] == 0:
            self.tab._toggle_all_buttons(True)

    def compact_action(self):
        params = BorgCompactJob.prepare(self.tab.profile())
        if params['ok']:
            job = BorgCompactJob(params['cmd'], params, self.tab.profile().repo.id)
            job.updated.connect(self.tab._set_status)
            job.result.connect(self.compact_result)
            self.tab._toggle_all_buttons(False)
            self.tab.app.jobs_manager.add_job(job)
        else:
            self.tab._set_status(params['message'])

    def compact_result(self, result):
        self.tab._toggle_all_buttons(True)

    def prune_action(self):
        params = BorgPruneJob.prepare(self.tab.profile())
        if params['ok']:
            job = BorgPruneJob(params['cmd'], params, self.tab.profile().repo.id)
            job.updated.connect(self.tab._set_status)
            job.result.connect(self.prune_result)
            self.tab._toggle_all_buttons(False)
            self.tab.app.jobs_manager.add_job(job)
        else:
            self.tab._set_status(params['message'])

    def prune_result(self, result):
        if result['returncode'] == 0:
            self.tab._set_status(self.tab.tr('Pruning finished.'))
            self.tab.refresh_archive_list()
        else:
            self.tab._toggle_all_buttons(True)

    def save_prune_setting(self, new_value=None):
        profile = self.tab.profile()
        for i in self.tab.prune_intervals:
            setattr(profile, f'prune_{i}', getattr(self.tab, f'prune_{i}').value())
        profile.prune_keep_within = self.tab.prune_keep_within.text()
        profile.save()
