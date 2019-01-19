from dateutil import parser
from .borg_thread import BorgThread
from vorta.models import ArchiveModel, RepoModel


class BorgListRepoThread(BorgThread):

    def log_event(self, msg):
        self.app.backup_log_event.emit(msg)

    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_log_event.emit(self.tr('Refreshing archives...'))

    def finished_event(self, result):
        self.app.backup_finished_event.emit(result)
        self.result.emit(result)
        self.app.backup_log_event.emit(self.tr('Refreshing archives done.'))

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
            if not result['data']:
                result['data'] = {}  # TODO: Workaround for tests. Can't read mock results 2x.
            remote_archives = result['data'].get('archives', [])

            # Delete archives that don't exist on the remote side
            for archive in ArchiveModel.select().where(ArchiveModel.repo == repo.id):
                if not list(filter(lambda s: s['id'] == archive.snapshot_id, remote_archives)):
                    archive.delete_instance()

            # Add remote archives we don't have locally.
            for archive in result['data'].get('archives', []):
                new_archive, _ = ArchiveModel.get_or_create(
                    snapshot_id=archive['id'],
                    defaults={
                        'repo': repo.id,
                        'name': archive['name'],
                        'time': parser.parse(archive['time'])
                    }
                )
                new_archive.save()
