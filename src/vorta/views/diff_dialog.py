from PyQt5 import QtCore, uic
from PyQt5.QtWidgets import QHeaderView, QTableView, QTableWidgetItem

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

        self.archiveTable.setRowCount(archiveTable.rowCount())
        for row in range(archiveTable.rowCount()):
            for column in range(archiveTable.columnCount()):
                try:
                    text = archiveTable.item(row, column).text()
                    self.archiveTable.setItem(row, column, QTableWidgetItem(text))
                except AttributeError:
                    self.archiveTable.setItem(row, column, QTableWidgetItem(''))
