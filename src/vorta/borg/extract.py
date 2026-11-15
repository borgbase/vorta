import tempfile

from PyQt6.QtCore import QModelIndex, Qt

from vorta.utils import borg_compat
from vorta.views.dialogs.archive.extract import ExtractTree, FileData, FileType
from vorta.views.partials.treemodel import FileSystemItem, path_to_str

from .borg_job import BorgJob

_FNMATCH_ESCAPES = {'*': '[*]', '?': '[?]', '[': '[[]'}


def _include_pattern(item: FileSystemItem[FileData]) -> str:
    """Return a pattern file line that includes `path`.

    Borg reads pattern files line by line and strips surrounding whitespace, with no
    escape mechanism. Paths containing line breaks or leading/trailing whitespace are
    therefore expressed as `fm:` patterns with those characters replaced by `?`.
    """
    path = path_to_str(item.path)
    # borg does a linear scan for pp but a hash lookup on pf. Only emit pp if this
    # might be a directory. Keeps the common case of user selects 1 directory fast
    # while handling some pathalogical cases of selecting 1 directory then unselecting
    # 1 child producing thousands of pp:'s requiring the linear scan each
    if '\n' not in path and '\r' not in path and path == path.strip():
        if item.data.file_type == FileType.DIRECTORY:
            return '+ pp:' + path
        return '+ pf:' + path

    stripped = path.lstrip()
    lead = len(path) - len(stripped)
    stripped = stripped.rstrip()
    trail = len(path) - lead - len(stripped)

    chars = []
    for i, c in enumerate(path):
        if c in '\n\r' or i < lead or i >= len(path) - trail:
            chars.append('?')
        else:
            chars.append(_FNMATCH_ESCAPES.get(c, c))
    return '+ fm:' + ''.join(chars)


class BorgExtractJob(BorgJob):
    emits_backup_finished = True

    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_progress_event.emit(
            f"[{self.params['profile_name']}] {self.tr('Downloading files from archive…')}"
        )

    def finished_event(self, result):
        self._emit_backup_finished(result)
        self._emit_result(result)
        self.app.backup_progress_event.emit(
            f"[{self.params['profile_name']}] {self.tr('Restored files from archive.')}"
        )

    @classmethod
    def prepare(cls, profile, archive_name, model: ExtractTree, destination_folder):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        cmd = ['borg', 'extract', '--list', '--info', '--log-json']
        cmd += borg_compat.repo_args(profile.repo.url, archive_name)

        # process selected items
        # all items will be excluded beside the one actively selected in the
        # dialog.
        # Unselected (and excluded) parent folders will be restored by borg
        # but without the metadata stored in the archive.
        pattern_file = tempfile.NamedTemporaryFile('w', delete=True)
        pattern_file.write("P pp\n")

        indexes = [model.index(i, 0, QModelIndex()) for i in range(model.rowCount(QModelIndex()))]
        while indexes:
            index = indexes.pop()

            checked = model.data(index, Qt.ItemDataRole.CheckStateRole)
            item: FileSystemItem[FileData] = index.internalPointer()
            if checked == Qt.CheckState.Checked:
                pattern_file.write(_include_pattern(item) + "\n")
            elif checked == Qt.CheckState.PartiallyChecked:
                for i in range(model.rowCount(index)):
                    indexes.append(model.index(i, 0, index))
            # else do neither because its not relevant

        pattern_file.write("- fm:*\n")
        pattern_file.flush()
        cmd.extend(['--patterns-from', pattern_file.name])
        ret['cleanup_files'].append(pattern_file)

        ret['ok'] = True
        ret['cmd'] = cmd
        ret['cwd'] = destination_folder

        return ret
