from .borg_job import BorgJob
from vorta.utils import format_archive_name


class BorgPruneJob(BorgJob):

    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_progress_event.emit(self.tr('Pruning old archives...'))

    def finished_event(self, result):
        self.app.backup_finished_event.emit(result)
        self.result.emit(result)
        self.app.backup_progress_event.emit(self.tr('Pruning done.'))

    @classmethod
    def prepare(cls, profile):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        cmd = ['borg', 'prune', '--list', '--info', '--log-json']

        pruning_opts = [
            '--keep-hourly', str(profile.prune_hour),
            '--keep-daily', str(profile.prune_day),
            '--keep-weekly', str(profile.prune_week),
            '--keep-monthly', str(profile.prune_month),
            '--keep-yearly', str(profile.prune_year),
        ]

        if profile.prune_prefix:
            formatted_prune_prefix = format_archive_name(profile, profile.prune_prefix)
            pruning_opts += ['--prefix', formatted_prune_prefix]

        if profile.prune_keep_within:
            pruning_opts += ['--keep-within', profile.prune_keep_within]
        cmd += pruning_opts
        cmd.append(f'{profile.repo.url}')

        ret['ok'] = True
        ret['cmd'] = cmd

        return ret
