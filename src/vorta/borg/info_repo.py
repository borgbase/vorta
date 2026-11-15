from PyQt6.QtCore import QT_TRANSLATE_NOOP

from vorta.store.models import RepoModel
from vorta.utils import borg_compat

from .borg_job import BorgJob, FakeProfile, FakeRepo


def encryption_mode(encryption):
    """
    Return a Borg 1 style mode like `repokey-blake2`, which Vorta stores and compares against.

    Borg >= 2.0.0b22 reports only the cipher name (`chacha20-poly1305`) plus `keyfile` when the key is stored
    as a keyfile, so the key storage is added here. Its plaintext ciphers (`none`, `none-sha256`, ...) map to `none`.
    """
    if 'mode' in encryption:
        return encryption['mode']
    name = encryption['encryption']
    if name == 'none' or name.startswith('none-'):
        return 'none'
    storage = 'keyfile' if 'keyfile' in encryption else 'repokey'
    return f'{storage}-{name}'


class BorgInfoRepoJob(BorgJob):
    def started_event(self):
        self.updated.emit(self.tr('Validating existing repo…'))

    @classmethod
    def prepare(cls, params):
        """
        Used to validate existing repository when added.
        """

        # Build fake profile because we don't have it in the DB yet. Assume unencrypted.
        profile = FakeProfile(
            999,
            FakeRepo(params['repo_url'], params['repo_name'], 999, params['extra_borg_arguments'], 'none'),
            'New Repo',
            params['ssh_key'],
        )

        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        if borg_compat.check('V2'):
            cmd = ["borg", "repo-info", "--info", "--json", "--log-json"]
        else:
            cmd = ["borg", "info", "--info", "--json", "--log-json"]
        cmd += borg_compat.repo_args(profile.repo.url)

        ret['additional_env'] = {
            'BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK': "yes",
            'BORG_RSH': 'ssh -oStrictHostKeyChecking=accept-new',
        }

        ret['password'] = params['password']  # Empty password is '', which disables prompt
        # Unlock now, even without a password, so process_result() can store the passphrase.
        unlocked = cls.keyring.try_unlock()
        if params['password'] != '' and not unlocked:
            # Cannot tell if repo has encryption, assuming based off of password
            ret['message'] = QT_TRANSLATE_NOOP('messages', 'Please unlock your password manager.')
            return ret

        ret['repo_name'] = params['repo_name']
        ret['ok'] = True
        ret['cmd'] = cmd

        return ret

    def process_result(self, result):
        if result['returncode'] == 0:
            data = result['data']
            # Parse before get_or_create(), so an unexpected shape cannot leave an orphan repo row.
            encryption = encryption_mode(data['encryption']) if 'encryption' in data else None
            stats = data.get('cache', {}).get('stats')  # Borg 2 has no cache stats

            new_repo, _ = RepoModel.get_or_create(
                url=result['params']['repo_url'], defaults={'name': result['params']['repo_name']}
            )
            if stats:
                new_repo.total_size = stats['total_size']
                new_repo.unique_size = stats['unique_size']
                new_repo.total_unique_chunks = stats['total_unique_chunks']
            if encryption is not None:
                new_repo.encryption = encryption
            if new_repo.encryption != 'none':
                self.keyring.set_password("vorta-repo", new_repo.url, result['params']['password'])
            new_repo.extra_borg_arguments = result['params']['extra_borg_arguments']

            new_repo.save()
