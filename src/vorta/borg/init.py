from .borg_thread import BorgThread, FakeProfile, FakeRepo
from vorta.models import RepoModel


class BorgInitThread(BorgThread):

    def started_event(self):
        self.updated.emit(self.tr('Setting up new repo...'))

    @classmethod
    def prepare(cls, params):

        # Build fake profile because we don't have it in the DB yet.
        profile = FakeProfile(
            FakeRepo(params['repo_url'], 999, params['extra_borg_arguments'],
                     params['encryption']), 'Init Repo', params['ssh_key']
        )

        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        cmd = ["borg", "init", "--info", "--log-json"]
        cmd.append(f"--encryption={params['encryption']}")
        cmd.append(params['repo_url'])

        ret['additional_env'] = {
            'BORG_RSH': 'ssh -oStrictHostKeyChecking=no'
        }

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
                    'encryption': result['params']['encryption'],
                    'extra_borg_arguments': result['params']['extra_borg_arguments'],
                }
            )
            if new_repo.encryption != 'none':
                self.keyring.set_password("vorta-repo", new_repo.url, result['params']['password'])
            new_repo.save()
