from PyQt5.QtGui import QIcon, QImage, QPixmap
from vorta.utils import get_asset, uses_dark_mode


def get_colored_icon(icon_name):
    """
    Return SVG icon in the correct color.
    """
    with open(get_asset(f"icons/{icon_name}.svg"), 'rb') as svg_file:
        svg_str = svg_file.read()
    if uses_dark_mode():
        svg_str = svg_str.replace(b'#000000', b'#ffffff')
    # Reduce image size to 128 height
    svg_img = QImage.fromData(svg_str).scaledToHeight(128)

    return QIcon(QPixmap(svg_img))
