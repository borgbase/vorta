from datetime import datetime as dt
from .borg_job import BorgJob
from vorta.store.models import ArchiveModel, RepoModel


class BorgListRepoJob(BorgJob):

    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_progress_event.emit(self.tr('Refreshing archives...'))

    def finished_event(self, result):
        self.app.backup_finished_event.emit(result)
        self.result.emit(result)
        self.app.backup_progress_event.emit(self.tr('Refreshing archives done.'))

    @classmethod
    def prepare(cls, profile):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        cmd = ['borg', 'list', '--info', '--log-json', '--json', '--format', '{id}{name}{start}{end}{NL}']
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
                if not list(filter(lambda s: s['name'] == archive.name, remote_archives)):
                    archive.delete_instance()

            # Add or update remote archives we don't have locally.
            for a in result['data'].get('archives', []):
                existing_archives = ArchiveModel.select().where(
                    ArchiveModel.repo == repo.id,
                    ArchiveModel.name == a['name']
                )
                if existing_archives.count() == 1:
                    archive = existing_archives.get()
                else:
                    archive = ArchiveModel(
                        name=a['name'],
                        repo=repo.id,
                        time=dt.fromisoformat(a['start'])
                    )
                archive.duration = (
                    dt.fromisoformat(a['end']) - dt.fromisoformat(a['start'])
                ).total_seconds()
                archive.save()
