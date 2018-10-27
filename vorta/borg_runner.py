import json
import os
import sys
import shutil
from PyQt5 import QtCore
import subprocess
from subprocess import Popen, PIPE


class BorgThread(QtCore.QThread):
    updated = QtCore.pyqtSignal(str)
    result = QtCore.pyqtSignal(object)

    def __init__(self, parent, cmd, params):
        super().__init__(parent)

        # Find packaged borg binary. Prefer globally installed.
        if not shutil.which('borg'):
            meipass_borg = os.path.join(sys._MEIPASS, 'bin', 'borg')
            if os.path.isfile(meipass_borg):
                cmd[0] = meipass_borg
        self.cmd = cmd

        env = os.environ.copy()
        if params.get('password'):
            env['BORG_PASSPHRASE'] = params['password']

        if params.get('ssh_key'):
            env['BORG_RSH'] = f'ssh -i ~/.ssh/{params["ssh_key"]}'
        self.env = env
        self.params = params

    def run(self):
        with Popen(self.cmd, stdout=PIPE, stderr=PIPE, bufsize=1, universal_newlines=True, env=self.env) as p:
            for line in p.stderr:
                parsed = json.loads(line)
                if parsed['type'] == 'log_message':
                    self.updated.emit(f'{parsed["levelname"]}: {parsed["message"]}')
                elif parsed['type'] == 'file_status':
                    self.updated.emit(f'{parsed["path"]} ({parsed["status"]})')

            p.wait()
            stdout = p.stdout.read()
            result = {
                'params': self.params,
                'returncode': p.returncode,
            }
            try:
                result['data'] = json.loads(stdout)
            except:
                result['data'] = {}

            self.result.emit(result)
