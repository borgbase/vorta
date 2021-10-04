from .borg_job import BorgJob
from vorta.i18n import trans_late


class BorgVersionJob(BorgJob):
    """
    Gets the path of the borg binary to be used and the borg version.

    Used to display under 'Misc' and later for version-specific compatibility.
    """

    def finished_event(self, result):
        self.result.emit(result)

    @classmethod
    def prepare(cls):
        ret = {'ok': False}

        if cls.prepare_bin() is None:
            ret['message'] = trans_late('messages', 'Borg binary was not found.')
            return ret

        ret['cmd'] = ['borg', '--version']
        ret['ok'] = True
        return ret

    def process_result(self, result):
        if result['returncode'] == 0:
            version = result['data'].strip().split(' ')[1]
            path = self.prepare_bin()
            result['data'] = {
                'version': version,
                'path': path
            }
