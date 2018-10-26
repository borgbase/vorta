import json
import os
from PyQt5 import QtCore
import subprocess
from subprocess import Popen, PIPE


class BorgThread(QtCore.QThread):
    updated = QtCore.pyqtSignal(str)
    result = QtCore.pyqtSignal(object)

    def __init__(self, parent, cmd, params):
        super().__init__(parent)
        self.cmd = cmd

        env = os.environ.copy()
        if params.get('password'):
            env['BORG_PASSPHRASE'] = params['password']

        if params.get('ssh_key'):
            env['BORG_RSH'] = f'ssh -i ~/.ssh/{params["ssh_key"]}'
        self.env = env
        self.params = params

    def run(self):
        self.updated.emit('Adding Repo...')
        with Popen(self.cmd, stdout=PIPE, stderr=PIPE, bufsize=1, universal_newlines=True, env=self.env) as p:
            for line in p.stderr:
                print(line)
                parsed = json.loads(line)
                self.updated.emit(f'{parsed["levelname"]}: {parsed["message"]}')

            p.wait()
            stdout = p.stdout.read()
            result = {
                'params': self.params,
                'returncode': p.returncode,
            }
            if stdout.strip():
                result['data'] = json.loads(stdout)

            self.result.emit(result)
