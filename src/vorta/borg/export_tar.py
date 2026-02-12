from vorta.utils import borg_compat

from .borg_job import BorgJob


class BorgExportTar(BorgJob):
    """
    Job to export an archive to a tarball.
    """

    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_progress_event.emit(
            f"[{self.params['profile_name']}] {self.tr('Exporting archive to tarball…')}"
        )

    def finished_event(self, result):
        self.app.backup_finished_event.emit(result)
        self.result.emit(result)
        self.app.backup_progress_event.emit(f"[{self.params['profile_name']}] {self.tr('Export to tarball finished.')}")

    @classmethod
    def prepare(
        cls,
        profile,
        archive_name,
        destination_file,
        compression=None,
        strip_components=0,
        paths=None,
        excludes=None,
        tar_format=None,
    ):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            # Set back to false, so we can do our own checks here.
            ret['ok'] = False

        cmd = ['borg', 'export-tar']

        if compression and compression != 'none':
            cmd.append(f'--tar-filter={compression}')

        if strip_components > 0:
            cmd.append(f'--strip-components={strip_components}')

        if excludes:
            for pattern in excludes:
                cmd.extend(['-e', pattern])

        if tar_format and borg_compat.check('V2') and tar_format != 'GNU':
            cmd.append(f'--tar-format={tar_format}')

        if borg_compat.check('V2'):
            cmd += ['-r', profile.repo.url, archive_name]
        else:
            cmd.append(f'{profile.repo.url}::{archive_name}')

        cmd.append(destination_file)

        if paths:
            cmd.extend(paths)

        ret['ok'] = True
        ret['cmd'] = cmd
        return ret
        ret['cmd'] = cmd

        return ret
