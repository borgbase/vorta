from .borg_job import BorgJob, FakeProfile, FakeRepo
from vorta.i18n import trans_late
from vorta.store.models import RepoModel


class BorgInfoRepoJob(BorgJob):

    def started_event(self):
        self.updated.emit(self.tr('Validating existing repo...'))

    @classmethod
    def prepare(cls, params):
        """
        Used to validate existing repository when added.
        """

        # Build fake profile because we don't have it in the DB yet. Assume unencrypted.
        profile = FakeProfile(
            999,
            FakeRepo(params['repo_url'], 999, params['extra_borg_arguments'], 'none'),
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

        ret['additional_env'] = {
            'BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK': "yes",
            'BORG_RSH': 'ssh -oStrictHostKeyChecking=no'
        }

        ret['password'] = params['password']  # Empty password is '', which disables prompt
        if params['password'] != '':
            # Cannot tell if repo has encryption, assuming based off of password
            if not cls.keyring.is_unlocked:
                ret['message'] = trans_late('messages', 'Please unlock your password manager.')
                return ret

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
                self.keyring.set_password("vorta-repo", new_repo.url, result['params']['password'])

            new_repo.extra_borg_arguments = result['params']['extra_borg_arguments']

            new_repo.save()
