import datetime
import platform

from PyQt6 import uic
from PyQt6.QtWidgets import QApplication

from vorta._version import __version__
from vorta.i18n import trans_late, translate
from vorta.i18n.richtext import escape, format_richtext, link
from vorta.utils import borg_compat
from vorta.views.utils import get_colored_icon

from ..utils import get_asset

# Load UI file
uifile = get_asset('UI/exception_dialog.ui')
ExceptionDialogUI, ExceptionDialogBase = uic.loadUiType(uifile)


class ExceptionDetails:
    @staticmethod
    def get_os_details():
        uname_result = platform.uname()
        os_details = f"OS: {uname_result.system}\n"
        os_details += f"Release: {uname_result.release}\n"
        os_details += f"Version: {uname_result.version}"
        return os_details

    @staticmethod
    def get_exception_details(exception):
        details = ExceptionDetails.get_os_details()
        details += "\nDate and Time: " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        details += "\nBorg Version: " + borg_compat.version
        details += "\nVorta Version: " + __version__
        details += "\n" + exception
        return details


class ExceptionDialog(ExceptionDialogBase, ExceptionDialogUI):
    def __init__(self, exception: str):
        super().__init__()
        self.setupUi(self)

        self.report_to_github_label.setOpenExternalLinks(True)
        self.ignoreButton.clicked.connect(self.close)
        self.copyButton.clicked.connect(self.copy_report_to_clipboard)

        self.report_issue_text = trans_late(
            'Dialog',
            'You can report this issue on %1. Please search for similar issues before reporting.',
        )
        self.report_issue_link_text = trans_late('Dialog', 'Github')
        self._set_report_link()

        self.copyButton.setIcon(get_colored_icon('copy'))

        # Set crash details
        details = ExceptionDetails.get_exception_details(exception)
        self.crashDetails.setPlainText(details)

        # Set alert image
        self.alertImage.setPixmap(get_colored_icon('exclamation-triangle', scaled_height=75, return_qpixmap=True))

    def _set_report_link(self):
        template = self.report_to_github_label.text()
        sentence_template = translate('Dialog', self.report_issue_text)
        link_text = translate('Dialog', self.report_issue_link_text)
        sentence = format_richtext(
            escape(sentence_template),
            link('https://github.com/borgbase/vorta/issues', link_text),
        )
        self.report_to_github_label.setText(format_richtext(template, sentence))

    def copy_report_to_clipboard(self):
        cb = QApplication.clipboard()
        cb.setText(self.crashDetails.toPlainText(), mode=cb.Mode.Clipboard)
