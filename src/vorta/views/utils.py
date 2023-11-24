import json
import os
import sys

from PyQt6.QtGui import QIcon, QImage, QPixmap

from vorta.utils import get_asset, uses_dark_mode


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
