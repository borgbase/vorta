from vorta.utils import borg_compat, format_archive_name

from .borg_job import BorgJob, invalidate_repo_stats


class BorgPruneJob(BorgJob):
    emits_backup_finished = True

    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {self.tr('Pruning old archives…')}")

    def process_result(self, result):
        invalidate_repo_stats(result['params']['repo_id'])

    def finished_event(self, result):
        self._emit_backup_finished(result)
        self._emit_result(result)
        self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {self.tr('Pruning done.')}")

    @classmethod
    def prepare(cls, profile):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        cmd = ['borg', 'prune', '--list', '--info', '--log-json']

        pruning_opts = [
            '--keep-hourly',
            str(profile.prune_hour),
            '--keep-daily',
            str(profile.prune_day),
            '--keep-weekly',
            str(profile.prune_week),
            '--keep-monthly',
            str(profile.prune_month),
            '--keep-yearly',
            str(profile.prune_year),
        ]

        if profile.prune_prefix:
            formatted_prune_prefix = format_archive_name(profile, profile.prune_prefix)

            if borg_compat.check('V2'):
                pruning_opts += ['-a', f"sh:{formatted_prune_prefix}*"]
            elif borg_compat.check('V122'):
                pruning_opts += ['-a', f"{formatted_prune_prefix}*"]
            else:
                pruning_opts += ['--prefix', formatted_prune_prefix]

        if profile.prune_keep_within:
            pruning_opts += ['--keep-within', profile.prune_keep_within]
        cmd += pruning_opts
        cmd += borg_compat.repo_args(profile.repo.url)

        ret['ok'] = True
        ret['cmd'] = cmd

        return ret
