from vorta.store.models import ArchiveModel, RepoModel
from .borg_job import BorgJob


class BorgRenameJob(BorgJob):

    def log_event(self, msg):
        self.app.backup_log_event.emit(msg)

    @classmethod
    def prepare(cls, profile):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        cmd = ['borg', 'rename', '--info', '--log-json']
        cmd.append(f'{profile.repo.url}')

        ret['ok'] = True
        ret['cmd'] = cmd

        return ret

    def process_result(self, result):
        if result['returncode'] == 0:
            repo_url, old_name = result['cmd'][-2].split('::')
            new_name = result['cmd'][-1]
            repo = RepoModel.get(url=repo_url)
            renamed_archive = ArchiveModel.get(name=old_name, repo=repo)
            renamed_archive.name = new_name
            renamed_archive.save()
