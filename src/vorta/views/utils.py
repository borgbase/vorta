from PyQt5 import QtCore
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QIcon, QImage, QPixmap

from vorta.i18n import translate
from vorta.utils import uses_dark_mode, get_asset
from vorta.models import BackupProfileModel


def get_colored_icon(icon_name):
    """
    Return SVG icon in the correct color.
    """
    svg_str = open(get_asset(f"icons/{icon_name}.svg"), 'rb').read()
    if uses_dark_mode():
        svg_str = svg_str.replace(b'#00000', b'#ffffff')
    # Reduce image size to 128 height
    svg_img = QImage.fromData(svg_str).scaledToHeight(128)

    return QIcon(QPixmap(svg_img))


def process_errors(self, context):
    cmd = context.get('cmd')
    if cmd is not None and cmd != 'init':
        msgid = context.get('msgid')
        repo_url = context.get('repo_url')
        if msgid == 'LockTimeout':
            profile = BackupProfileModel.get(name=context['profile_name'])
            msg = QMessageBox()
            self.msg = msg  # for tests
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setParent(self, QtCore.Qt.Sheet)
            msg.setText(
                translate(
                    "MainWindow QMessagebox",
                    f"The repository at {repo_url} might be in use by another computer. Continue?"))
            msg.button(QMessageBox.Yes).clicked.connect(lambda: self.break_lock(profile))
            msg.setWindowTitle(translate("MainWindow QMessagebox", "Repository In Use"))
            msg.show()
        elif msgid == 'LockFailed':
            msg = QMessageBox()
            self.msg = msg  # for tests
            msg.setParent(self, QtCore.Qt.Sheet)
            msg.setText(
                translate(
                    "MainWindow QMessagebox",
                    f"You do not have permission to access the repository at {repo_url}. Gain access and try again."))
            msg.setWindowTitle(translate("MainWindow QMessagebox", "No Repository Permissions"))
            msg.show()
