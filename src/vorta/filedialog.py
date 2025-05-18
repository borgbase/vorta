from PyQt6.QtCore import QDir
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QTreeView, QVBoxLayout


class VortaFileDialog(QDialog):
    def __init__(self, parent=None, title='Select files and folders:'):
        super().__init__(parent)
        self.setWindowTitle(self.tr('Add Files and Folders'))
        self.resize(600, 400)

        layout = QVBoxLayout(self)

        self.label = QLabel(self.tr(title))
        layout.addWidget(self.label)

        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())

        # Allow files and directories except '.' and '..'
        self.model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)
        self.model.directoryLoaded.connect(lambda _: self.tree.resizeColumnToContents(0))

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(QDir.homePath()))
        self.tree.setSelectionMode(QTreeView.SelectionMode.ExtendedSelection)
        self.tree.setHeaderHidden(True)

        # Resize the width when the directory is collapsed/expanded
        self.tree.expanded.connect(lambda _: self.tree.resizeColumnToContents(0))
        self.tree.collapsed.connect(lambda _: self.tree.resizeColumnToContents(0))

        layout.addWidget(self.tree)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_paths(self):
        indexes = self.tree.selectionModel().selectedIndexes()
        paths = []
        for index in indexes:
            if index.column() == 0:
                path = self.model.filePath(index)
                paths.append(path)
        # Remove duplicate paths
        return list(set(paths))


class VortaFileSelector:
    @staticmethod
    def get_paths(parent=None, title='Select files and folders:'):
        dialog = VortaFileDialog(parent, title)
        if dialog.exec():
            return dialog.selected_paths()
        return []
