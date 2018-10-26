import os
from PyQt5 import uic
from .borg_runner import BorgThread

uifile = os.path.join(os.path.dirname(__file__), 'UI/initrepo.ui')
InitRepoUI, InitRepoBase = uic.loadUiType(uifile)


class InitRepoWindow(InitRepoBase, InitRepoUI):
    def __init__(self, cmd, env):
        super().__init__()
        self.setupUi(self)
        self.closeButton.clicked.connect(self.close)

        self._thread = BorgThread(self, cmd, env)
        self._thread.updated.connect(self.update_log)
        self._thread.result.connect(self.get_result)

    def update_log(self, text):
            self.logText.appendPlainText(text)

    def get_result(self, result):
        if result['returncode'] == 0:
            self.logText.appendPlainText('Finished successfully.')
            self.closeButton.setEnabled(True)
        else:
            self.logText.appendPlainText('Finished with errors.')
            self.closeButton.setEnabled(True)
