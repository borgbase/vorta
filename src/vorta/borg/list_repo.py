import logging
from datetime import datetime as dt

from vorta.store.models import ArchiveModel, RepoModel
from vorta.utils import borg_compat

from .borg_job import BorgJob

logger = logging.getLogger(__name__)


class BorgListRepoJob(BorgJob):
    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {self.tr('Refreshing archives…')}")

    def finished_event(self, result):
        self.app.backup_finished_event.emit(result)
        self.result.emit(result)
        self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {self.tr('Refreshing archives done.')}")

    @classmethod
    def prepare(cls, profile):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        if borg_compat.check('V2'):
            cmd = ['borg', 'repo-list', '--info', '--log-json', '--json', '-r']
        else:
            cmd = ['borg', 'list', '--info', '--log-json', '--json']
        cmd.append(f'{profile.repo.url}')

        ret['ok'] = True
        ret['cmd'] = cmd

        return ret

    def process_result(self, result):
        if result['returncode'] != 0:
            return

        data = result['data']
        if not isinstance(data, dict) or not isinstance(data.get('archives'), list):
            # Never treat unreadable output as "no archives" - that would wipe the local list.
            msg = self.tr('Could not read archive list from Borg. Local list kept.')
            logger.warning('Unexpected borg list output (%s): %.200r', type(data).__name__, data)
            result['errors'].append((logging.WARNING, msg))
            result['ok'] = False
            return

        repo, _ = RepoModel.get_or_create(url=result['cmd'][-1])
        remote_archives = data['archives']
        remote_ids = {a['id'] for a in remote_archives}

        # Delete archives that don't exist on the remote side
        for archive in ArchiveModel.select().where(ArchiveModel.repo == repo.id):
            if archive.snapshot_id not in remote_ids:
                archive.delete_instance()

        # Add remote archives we don't have locally.
        for archive in remote_archives:
            new_archive, _ = ArchiveModel.get_or_create(
                snapshot_id=archive['id'],
                repo=repo.id,
                defaults={
                    'name': archive['name'],
                    # Convert to local time (for Borg 2.x UTC timestamps) before storing as naive datetime
                    'time': dt.fromisoformat(archive['time']).astimezone().replace(tzinfo=None),
                },
            )
            new_archive.save()
