from vorta.store.models import ArchiveModel, RepoModel
from vorta.utils import borg_compat

from .borg_job import BorgJob


class BorgInfoArchiveJob(BorgJob):
    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {self.tr('Refreshing archive…')}")

    def finished_event(self, result):
        self.app.backup_finished_event.emit(result)
        self.result.emit(result)
        self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {self.tr('Refreshing archive done.')}")

    @classmethod
    def prepare(cls, profile, archive_name):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret

        ret['ok'] = True
        ret['cmd'] = ['borg', 'info', '--log-json', '--json']
        if borg_compat.check('V2'):
            ret['cmd'].extend(["-r", profile.repo.url, '-a', archive_name])
        else:
            ret['cmd'].append(f'{profile.repo.url}::{archive_name}')
        ret['archive_name'] = archive_name

        return ret

    def process_result(self, result):
        if result['returncode'] == 0:
            remote_archives = result['data'].get('archives', [])

            # get info stored during BorgJob.prepare()
            # repo_id = self.params['repo_id']
            repo_id = result['params']['repo_id']

            # Update remote archives.
            for remote_archive in remote_archives:
                archive = ArchiveModel.get_or_none(snapshot_id=remote_archive['id'], repo=repo_id)
                if archive is None:
                    # archive id was changed during rename, so we need to find it by name
                    archive = ArchiveModel.get_or_none(name=remote_archive['name'], repo=repo_id)
                    archive.snapshot_id = remote_archive['id']

                archive.name = remote_archive['name']  # incase name changed
                # archive.time = parser.parse(remote_archive['time'])
                archive.duration = remote_archive['duration']
                archive.size = remote_archive['stats']['deduplicated_size']

                archive.save()

            if 'cache' in result['data']:
                stats = result['data']['cache']['stats']
                repo = RepoModel.get(id=result['params']['repo_id'])
                repo.total_size = stats['total_size']
                repo.unique_size = stats['unique_size']
                repo.total_unique_chunks = stats['total_unique_chunks']
                repo.save()
