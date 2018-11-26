from dateutil import parser
from .borg_thread import BorgThread
from vorta.models import ArchiveModel, RepoModel


class BorgListRepoThread(BorgThread):

    def log_event(self, msg):
        self.app.backup_log_event.emit(msg)

    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_log_event.emit('Refreshing snapshots..')

    def finished_event(self, result):
        self.app.backup_finished_event.emit(result)
        self.result.emit(result)
        self.app.backup_log_event.emit('Refreshing snapshots done.')

    @classmethod
    def prepare(cls, profile):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        cmd = ['borg', 'list', '--info', '--log-json', '--json']
        cmd.append(f'{profile.repo.url}')

        ret['ok'] = True
        ret['cmd'] = cmd

        return ret

    def process_result(self, result):
        if result['returncode'] == 0:
            repo, created = RepoModel.get_or_create(url=result['cmd'][-1])
            remote_snapshots = result['data'].get('archives', [])

            # Delete snapshots that don't exist on the remote side
            for snapshot in ArchiveModel.select().where(ArchiveModel.repo == repo.id):
                if not list(filter(lambda s: s['id'] == snapshot.snapshot_id, remote_snapshots)):
                    snapshot.delete_instance()

            # Add remote snapshots we don't have locally.
            for snapshot in result['data'].get('archives', []):
                new_snapshot, _ = ArchiveModel.get_or_create(
                    snapshot_id=snapshot['id'],
                    defaults={
                        'repo': repo.id,
                        'name': snapshot['name'],
                        'time': parser.parse(snapshot['time'])
                    }
                )
                new_snapshot.save()
