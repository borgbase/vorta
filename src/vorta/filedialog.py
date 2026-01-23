import os

from PyQt6.QtCore import QDir, Qt
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtWidgets import (
    QCheckBox,
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
    def __init__(self, parent=None, window_title='Vorta File Dialog', title='Select files and folders:'):
        super().__init__(parent)
        if parent:
            self.setParent(parent, Qt.WindowType.Sheet)

        self.setWindowTitle(self.tr(window_title))
        self.resize(600, 400)

        layout = QVBoxLayout(self)
        path_layout = QHBoxLayout()
        bottom_layout = QHBoxLayout()

        # Show hidden files checkbox
        self.showHidden = QCheckBox(self.tr('Show hidden files'))
        self.showHidden.stateChanged.connect(self.show_hidden_files)
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

        bottom_layout.addWidget(self.showHidden)
        bottom_layout.addWidget(buttons)
        layout.addLayout(bottom_layout)

        # Connections
        self.btnHome.clicked.connect(self.go_home)
        self.btnUp.clicked.connect(self.go_up)

    def selected_paths(self):
        indexes = self.tree.selectionModel().selectedIndexes()
        paths = []

        # If no tree selection, use the path bar text as the selection
        if not indexes:
            path = self.path_bar.text()
            if path and os.path.exists(path):
                if not os.access(path, os.R_OK):
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Icon.Warning)
                    msg.setWindowTitle(self.tr("Permission Denied"))
                    msg.setText(self.tr(f"You don't have read access to {path}."))
                    msg.exec()
                    return []
                return [path]
            return []

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
                    return []
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

    def show_hidden_files(self, state):
        if state:
            self.model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot | QDir.Filter.Hidden)
        else:
            self.model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)


class VortaFileSelector:
    def __init__(self, parent=None, window_title='Vorta File Dialog', title='Select files and folders:'):
        self.parent = parent
        self.title = title
        self.window_title = window_title

    def get_paths(self):
        dialog = VortaFileDialog(self.parent, self.window_title, self.title)
        if dialog.exec():
            return dialog.selected_paths()
        return []
