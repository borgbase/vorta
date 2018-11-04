from .borg_thread import BorgThread


class BorgPruneThread(BorgThread):

    def started_event(self):
        self.updated.emit('Pruning started')

    @classmethod
    def prepare(cls):
        profile = cls.profile()
        ret = super().prepare()
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
            '--keep-yearly', str(profile.prune_year)
        ]
        cmd += pruning_opts
        cmd.append(f'{profile.repo.url}')

        ret['ok'] = True
        ret['cmd'] = cmd

        return ret
