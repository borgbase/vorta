from .borg_job import BorgJob


class BorgCheckJob(BorgJob):

    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_progress_event.emit(self.tr('Starting consistency check...'))

    def finished_event(self, result):
        self.app.backup_finished_event.emit(result)
        self.result.emit(result)
        if result['returncode'] != 0:
            self.app.backup_progress_event.emit(self.tr('Repo check failed. See logs for details.'))
            self.app.check_failed_event.emit(self.params['repo_url'])
        else:
            self.app.backup_progress_event.emit(self.tr('Check completed.'))

    @classmethod
    def prepare(cls, profile):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        cmd = ['borg', 'check', '--info', '--log-json']
        cmd.append(f'{profile.repo.url}')

        ret['ok'] = True
        ret['cmd'] = cmd

        return ret
