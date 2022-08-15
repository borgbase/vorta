import tempfile
from PyQt5.QtCore import QModelIndex, Qt
from vorta.views.extract_dialog import ExtractTree, FileData
from vorta.views.partials.treemodel import FileSystemItem, path_to_str
from .borg_job import BorgJob


class BorgExtractJob(BorgJob):
    def started_event(self):
        self.app.backup_started_event.emit()
        self.app.backup_progress_event.emit(self.tr('Downloading files from archive…'))

    def finished_event(self, result):
        self.app.backup_finished_event.emit(result)
        self.result.emit(result)
        self.app.backup_progress_event.emit(self.tr('Restored files from archive.'))

    @classmethod
    def prepare(cls, profile, archive_name, model: ExtractTree, destination_folder):
        ret = super().prepare(profile)
        if not ret['ok']:
            return ret
        else:
            ret['ok'] = False  # Set back to false, so we can do our own checks here.

        cmd = ['borg', 'extract', '--list', '--info', '--log-json']
        cmd.append(f'{profile.repo.url}::{archive_name}')

        # process selected items
        # all items will be excluded beside the one actively selected in the
        # dialog.
        # Unselected (and excluded) parent folders will be restored by borg
        # but without the metadata stored in the archive.
        pattern_file = tempfile.NamedTemporaryFile('w', delete=True)
        pattern_file.write("P fm\n")

        indexes = [QModelIndex()]
        while indexes:
            index = indexes.pop()

            for i in range(model.rowCount(index)):
                new_index = model.index(i, 0, index)
                indexes.append(new_index)

                item: FileSystemItem[FileData] = new_index.internalPointer()
                if item.data.checkstate == Qt.CheckState.Checked:
                    pattern_file.write("+ " + path_to_str(item.path) + "\n")

        pattern_file.write("- *\n")
        pattern_file.flush()
        pattern_file.close()  # wont delete temp file
        cmd.extend(['--patterns-from', pattern_file.name])
        ret['cleanup_files'].append(pattern_file)

        ret['ok'] = True
        ret['cmd'] = cmd
        ret['cwd'] = destination_folder

        return ret

    def process_result(self, result: dict):
        pass
