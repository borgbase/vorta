import json
import os
import sys

from PyQt6.QtGui import QIcon, QImage, QPixmap
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTableWidgetItem

from vorta.utils import get_asset, uses_dark_mode


class SizeItem(QTableWidgetItem):
    def __init__(self, s):
        super().__init__(s)
        self.setTextAlignment(Qt.AlignmentFlag.AlignVCenter + Qt.AlignmentFlag.AlignRight)

    def __lt__(self, other):
        if other.text() == '':
            return False
        elif self.text() == '':
            return True
        else:
            return sort_sizes([self.text(), other.text()]) == [
                self.text(),
                other.text(),
            ]


def sort_sizes(size_list):
    """Sorts sizes with extensions. Assumes that size is already in largest unit possible"""
    final_list = []
    for suffix in [" B", " KB", " MB", " GB", " TB", " PB", " EB", " ZB", " YB"]:
        sub_list = [
            float(size[: -len(suffix)])
            for size in size_list
            if size.endswith(suffix) and size[: -len(suffix)][-1].isnumeric()
        ]
        sub_list.sort()
        final_list += [(str(size) + suffix) for size in sub_list]
        # Skip additional loops
        if len(final_list) == len(size_list):
            break
    return final_list


def get_colored_icon(icon_name, scaled_height=128, return_qpixmap=False):
    """
    Return SVG icon in the correct color.
    """
    with open(get_asset(f"icons/{icon_name}.svg"), 'rb') as svg_file:
        svg_str = svg_file.read()
    if uses_dark_mode():
        svg_str = svg_str.replace(b'#000000', b'#ffffff')
    svg_img = QImage.fromData(svg_str).scaledToHeight(scaled_height)

    if return_qpixmap:
        return QPixmap(svg_img)
    else:
        return QIcon(QPixmap(svg_img))


def get_exclusion_presets():
    """
    Loads exclusion presets from JSON files in assets/exclusion_presets.

    Currently the preset name is used as identifier.
    """
    allPresets = {}
    os_tag = f"os:{sys.platform}"
    if getattr(sys, 'frozen', False):
        # we are running in a bundle
        bundle_dir = os.path.join(sys._MEIPASS, 'assets/exclusion_presets')
    else:
        # we are running in a normal Python environment
        bundle_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../assets/exclusion_presets')

    for preset_file in sorted(os.listdir(bundle_dir)):
        with open(os.path.join(bundle_dir, preset_file), 'r') as f:
            preset_list = json.load(f)
            for preset in preset_list:
                if os_tag in preset['tags']:
                    allPresets[preset['slug']] = {
                        'name': preset['name'],
                        'patterns': preset['patterns'],
                        'tags': preset['tags'],
                    }
    return allPresets
