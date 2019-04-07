from PyQt5.QtCore import QTextStream
from PyQt5.QtNetwork import QLocalSocket, QLocalServer
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import pyqtSignal


class QtSingleApplication(QApplication):
    """
    Adapted from https://stackoverflow.com/a/12712362/11038610

    Published by Johan Rade under 2-clause BSD license, opensource.org/licenses/BSD-2-Clause
    """
    message_received_event = pyqtSignal(str)

    def __init__(self, id, *argv):

        super().__init__(*argv)
        self._id = id

        # Is there another instance running?
        self._outSocket = QLocalSocket()
        self._outSocket.connectToServer(self._id)
        self._isRunning = self._outSocket.waitForConnected()

        if self._isRunning:
            # Yes, there is.
            self._outStream = QTextStream(self._outSocket)
            self._outStream.setCodec('UTF-8')
        else:
            # No, there isn't.
            self._outSocket = None
            self._outStream = None
            self._inSocket = None
            self._inStream = None
            self._server = QLocalServer()
            self._server.removeServer(self._id)
            self._server.listen(self._id)
            self._server.newConnection.connect(self._onNewConnection)

    def isRunning(self):
        return self._isRunning

    def id(self):
        return self._id

    def sendMessage(self, msg):
        if not self._outStream:
            return False
        self._outStream << msg << '\n'
        self._outStream.flush()
        return self._outSocket.waitForBytesWritten()

    def _onNewConnection(self):
        if self._inSocket:
            self._inSocket.readyRead.disconnect(self._onReadyRead)
        self._inSocket = self._server.nextPendingConnection()
        if not self._inSocket:
            return
        self._inStream = QTextStream(self._inSocket)
        self._inStream.setCodec('UTF-8')
        self._inSocket.readyRead.connect(self._onReadyRead)

    def _onReadyRead(self):
        while True:
            msg = self._inStream.readLine()
            if not msg:
                break
            self.message_received_event.emit(msg)
