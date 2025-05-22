import os

from PyQt6.QtCore import QDir
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
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
        self.btnHome.setIcon(get_colored_icon('home'))
        # Up button
        self.btnUp = QPushButton()
        self.btnUp.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btnUp.setIcon(get_colored_icon('folder-on-top'))
        # Path bar
        self.path_bar = QLineEdit()
        self.path_bar.setText(QDir.homePath())
        self.path_bar.textChanged.connect(self.path_changed)

        # Path bar layout
        path_layout.addWidget(self.btnHome)
        path_layout.addWidget(self.path_bar)
        path_layout.addWidget(self.btnUp)
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

        # Button connections
        self.btnHome.clicked.connect(self.go_home)
        self.btnUp.clicked.connect(self.go_up)

    def selected_paths(self):
        indexes = self.tree.selectionModel().selectedIndexes()
        paths = []
        for index in indexes:
            if index.column() == 0:
                path = self.model.filePath(index)
                # Check for read access
                if not os.access(path, os.R_OK):
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Icon.Warning)
                    msg.setWindowTitle(self.tr("Permission Denied"))
                    msg.setText(self.tr(f"You don't have read access to {path}."))
                    msg.exec()
                    return
                paths.append(path)
        return list(set(paths))  # remove duplicates

    def path_changed(self):
        path = self.path_bar.text()
        if os.path.exists(path):
            self.tree.setRootIndex(self.model.index(path))
            self.tree.resizeColumnToContents(0)
            self.path_bar.setStyleSheet("")
        else:
            self.path_bar.setStyleSheet("background-color: #ffcccc")

    def go_home(self):
        self.path_bar.setText(QDir.homePath())

    def go_up(self):
        current_path = self.path_bar.text()
        parent_path = os.path.dirname(current_path.rstrip(os.sep))

        # Prevent going above the root directory
        if not parent_path or not os.path.exists(parent_path):
            return

        self.path_bar.setText(parent_path)


class VortaFileSelector:
    @staticmethod
    def get_paths(parent=None, title='Select files and folders:'):
        dialog = VortaFileDialog(parent, title)
        if dialog.exec():
            return dialog.selected_paths()
        return []
