from collections import namedtuple
from .borg_thread import BorgThread
from vorta.models import RepoModel
from vorta.utils import keyring

FakeRepo = namedtuple('Repo', ['url', 'id', 'extra_borg_arguments'])
FakeProfile = namedtuple('FakeProfile', ['repo', 'name', 'ssh_key'])


class BorgInfoThread(BorgThread):

    def started_event(self):
        self.updated.emit(self.tr('Validating existing repo...'))

    @classmethod
    def prepare(cls, params):
        """
        Used to validate existing repository when added.
        """

        # Build fake profile because we don't have it in the DB yet.
        profile = FakeProfile(
            FakeRepo(params['repo_url'], 999, params['extra_borg_arguments']),
            'New Repo',
            params['ssh_key']
        )

        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        cmd = ["borg", "info", "--info", "--json", "--log-json"]
        cmd.append(profile.repo.url)

        if params['password'] == '':
            ret['password'] = '999999'  # Dummy password if the user didn't supply one. To avoid prompt.
        else:
            ret['password'] = params['password']
        ret['ok'] = True
        ret['cmd'] = cmd

        return ret

    def process_result(self, result):
        if result['returncode'] == 0:
            new_repo, _ = RepoModel.get_or_create(
                url=result['cmd'][-1]
            )
            if 'cache' in result['data']:
                stats = result['data']['cache']['stats']
                new_repo.total_size = stats['total_size']
                new_repo.unique_csize = stats['unique_csize']
                new_repo.unique_size = stats['unique_size']
                new_repo.total_unique_chunks = stats['total_unique_chunks']
            if 'encryption' in result['data']:
                new_repo.encryption = result['data']['encryption']['mode']
            if new_repo.encryption != 'none':
                keyring.set_password("vorta-repo", new_repo.url, result['params']['password'])

            new_repo.extra_borg_arguments = result['params']['extra_borg_arguments']

            new_repo.save()
