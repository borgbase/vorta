from dateutil import parser
from .borg_thread import BorgThread
from vorta.models import SnapshotModel

class BorgListThread(BorgThread):

    def started_event(self):
        self.updated.emit('Refreshing snapshots')

    @classmethod
    def prepare(cls):
        profile = cls.profile()
        ret = super().prepare()
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
        profile = self.profile()
        if result['returncode'] == 0:
            remote_snapshots = result['data']['archives']

            # Delete snapshots that don't exist on the remote side
            for snapshot in SnapshotModel.select().where(SnapshotModel.repo == profile.repo.id):
                if not list(filter(lambda s: s['id'] == snapshot.snapshot_id, remote_snapshots)):
                    snapshot.delete_instance()

            # Add remote snapshots we don't have locally.
            for snapshot in result['data']['archives']:
                new_snapshot, _ = SnapshotModel.get_or_create(
                    snapshot_id=snapshot['id'],
                    defaults={
                        'repo': profile.repo.id,
                        'name': snapshot['name'],
                        'time': parser.parse(snapshot['time'])
                    }
                )
                new_snapshot.save()
