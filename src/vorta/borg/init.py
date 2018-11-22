from .borg_thread import BorgThread
from .info import FakeProfile, FakeRepo
from vorta.models import RepoModel
from vorta.utils import keyring


class BorgInitThread(BorgThread):

    def started_event(self):
        self.updated.emit('Setting up new repo...')

    @classmethod
    def prepare(cls, params):

        # Build fake profile because we don't have it in the DB yet.
        profile = FakeProfile(
            FakeRepo(params['repo_url'], 999), 'Init Repo', params['ssh_key']
        )

        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        cmd = ["borg", "init", "--info", "--log-json"]
        cmd.append(f"--encryption={params['encryption']}")
        cmd.append(params['repo_url'])

        ret['encryption'] = params['encryption']
        ret['password'] = params['password']
        ret['ok'] = True
        ret['cmd'] = cmd

        return ret

    def process_result(self, result):
        if result['returncode'] == 0:
            new_repo, created = RepoModel.get_or_create(
                url=result['params']['repo_url'],
                defaults={
                    'encryption': result['params']['encryption']
                }
            )
            if new_repo.encryption != 'none':
                keyring.set_password("vorta-repo", new_repo.url, result['params']['password'])
            new_repo.save()
