import os

from PyQt6.QtCore import QDir
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTreeView,
    QVBoxLayout,
)

from vorta.views.utils import get_colored_icon


class VortaFileDialog(QDialog):
    def __init__(self, parent=None, title='Select files and folders:'):
        super().__init__(parent)
        self.setWindowTitle(self.tr('Add Files and Folders'))
        self.resize(600, 400)

        layout = QVBoxLayout(self)
        path_layout = QHBoxLayout()

        # Home button
        self.btnHome = QPushButton()
        self.btnHome.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        path_layout.addWidget(self.btnHome)
        self.btnHome.setIcon(get_colored_icon('home'))

        # Path bar
        self.path_bar = QLineEdit()
        path_layout.addWidget(self.path_bar)
        self.path_bar.setText(QDir.homePath())
        self.path_bar.textChanged.connect(self.path_changed)

        layout.addLayout(path_layout)

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
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Add")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.btnHome.clicked.connect(self.goto_home)

    def selected_paths(self):
        indexes = self.tree.selectionModel().selectedIndexes()
        paths = []
        for index in indexes:
            if index.column() == 0:
                path = self.model.filePath(index)
                paths.append(path)
        # Remove duplicate paths
        return list(set(paths))

    def path_changed(self):
        path = self.path_bar.text()
        if os.path.exists(path):
            self.tree.setRootIndex(self.model.index(path))
            self.tree.resizeColumnToContents(0)
            self.path_bar.setStyleSheet("")
        else:
            self.path_bar.setStyleSheet("background-color: #ffcccc")

    def goto_home(self):
        self.path_bar.setText(QDir.homePath())


class VortaFileSelector:
    @staticmethod
    def get_paths(parent=None, title='Select files and folders:'):
        dialog = VortaFileDialog(parent, title)
        if dialog.exec():
            return dialog.selected_paths()
        return []
