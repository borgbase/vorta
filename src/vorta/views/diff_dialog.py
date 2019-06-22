from PyQt5 import QtCore, uic
from PyQt5.QtWidgets import QHeaderView, QTableView, QTableWidgetItem
from PyQt5.QtCore import QItemSelectionModel

from vorta.utils import get_asset

uifile = get_asset('UI/diffdialog.ui')
DiffDialogUI, DiffDialogBase = uic.loadUiType(uifile)


class DiffDialog(DiffDialogBase, DiffDialogUI):

    def __init__(self, archiveTable):
        super().__init__()
        self.setupUi(self)

        header = self.archiveTable.horizontalHeader()
        header.setVisible(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setStretchLastSection(True)

        self.archiveTable.setSelectionBehavior(QTableView.SelectRows)
        self.archiveTable.setSelectionMode(QTableView.MultiSelection)
        self.archiveTable.setEditTriggers(QTableView.NoEditTriggers)
        self.archiveTable.setWordWrap(False)
        self.archiveTable.setTextElideMode(QtCore.Qt.ElideLeft)
        self.archiveTable.setAlternatingRowColors(True)
        self.archiveTable.itemSelectionChanged.connect(self.itemSelectionChanged_action)

        self.archiveTable.setRowCount(archiveTable.rowCount())
        for row in range(archiveTable.rowCount()):
            for column in range(archiveTable.columnCount()):
                try:
                    text = archiveTable.item(row, column).text()
                    self.archiveTable.setItem(row, column, QTableWidgetItem(text))
                except AttributeError:
                    self.archiveTable.setItem(row, column, QTableWidgetItem(''))

        self.cancelButton.clicked.connect(self.close)
        self.diffButton.clicked.connect(self.diff_action)
        self.selected_archives = None
        self.manual_change = True

    def diff_action(self):
        rows_selected = self.archiveTable.selectionModel().selectedRows()
        self.selected_archives = (rows_selected[0].row(), rows_selected[1].row())
        self.accept()

    def itemSelectionChanged_action(self):
        # Makes sure that not more than two rows are selected
        if self.manual_change:
            self.manual_change = False
            lst = self.archiveTable.selectionModel().selectedIndexes()
            if len(lst) > self.archiveTable.columnCount() * 2:
                for index in lst[:self.archiveTable.columnCount()]:
                    self.archiveTable.selectionModel().select(index, QItemSelectionModel.Deselect)
            self.manual_change = True
