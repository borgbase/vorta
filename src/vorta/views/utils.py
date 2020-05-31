from PyQt5.QtGui import QIcon, QImage, QPixmap
from vorta.utils import uses_dark_mode, get_asset


def get_colored_icon(icon_name):
    """
    Return SVG icon in the correct color.
    """
    svg_str = open(get_asset(f"icons/{icon_name}.svg"), 'rb').read()
    if uses_dark_mode():
        svg_str = svg_str.replace(b'#00000', b'#ffffff')
    svg_img = QImage.fromData(svg_str)
    return QIcon(QPixmap(svg_img))
