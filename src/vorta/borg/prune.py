from .borg_thread import BorgThread


class BorgPruneThread(BorgThread):
    def process_result(self, result):
        pass

    def log_event(self, msg):
        self.app.backup_log_event.emit(msg)

    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_log_event.emit('Backup started.')

    def finished_event(self, result):
        self.app.backup_finished_event.emit(result)

    @classmethod
    def prepare(cls):
        ret, params, profile = super().prepare()
        cmd = ['borg', 'prune', '--list', '--stats', '--info', '--log-json', '--json', ]

        # -H, --keep-hourly	number of hourly archives to keep
        # -d, --keep-daily	number of daily archives to keep
        # -w, --keep-weekly	number of weekly archives to keep
        # -m, --keep-monthly	number of monthly archives to keep
        # -y, --keep-yearly	number of yearly archives to keep

        ret['message'] = 'Pruning repository..'
        ret['ok'] = True
        ret['cmd'] = cmd
        ret['params'] = params

        return ret
