from vorta.store.models import RepoModel
from vorta.utils import borg_compat, format_archive_name

from .borg_job import BorgJob


class BorgPruneJob(BorgJob):
    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {self.tr('Pruning old archives…')}")

    def finished_event(self, result):
        # set repo stats to N/A
        repo = RepoModel.get(id=result['params']['repo_id'])
        repo.total_size = None
        repo.unique_csize = None
        repo.unique_size = None
        repo.total_unique_chunks = None
        repo.save()

        self.app.backup_finished_event.emit(result)
        self.result.emit(result)
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
        if borg_compat.check('V2'):
            cmd.extend(["-r", profile.repo.url])
        else:
            cmd.append(f'{profile.repo.url}')

        ret['ok'] = True
        ret['cmd'] = cmd

        return ret
