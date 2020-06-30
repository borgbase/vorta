from .borg_thread import BorgThread
from vorta.models import BackupProfileMixin, BackupProfileModel


class BorgConfigThread(BorgThread):
    @classmethod
    def prepare(cls, profile, values):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        cmd = ['borg', 'config', '--info', '--log-json']
        cmd.append(f'{profile.repo.url}')
        cmd.extend(values)

        ret['ok'] = True
        ret['cmd'] = cmd

        return ret

    def process_result(self, result):
        return result['cmd']
