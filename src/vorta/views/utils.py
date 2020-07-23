from PyQt5.QtGui import QIcon, QImage, QPixmap
from vorta.utils import uses_dark_mode, get_asset
from vorta.keyring.abc import VortaKeyring
from vorta.utils import logger, trans_late

keyring = VortaKeyring.get_keyring()
logger.info('Using %s Keyring implementation.', keyring.__class__.__name__)

def get_colored_icon(icon_name):
    """
    Return SVG icon in the correct color.
    """
    svg_str = open(get_asset(f"icons/{icon_name}.svg"), 'rb').read()
    if uses_dark_mode():
        svg_str = svg_str.replace(b'#00000', b'#ffffff')
    svg_img = QImage.fromData(svg_str)
    return QIcon(QPixmap(svg_img))


def validate_passwords(firstPass, secondPass):
    msg = ""
    passEqual = firstPass == secondPass
    passLong = len(firstPass) > 8

    if not passEqual:
        msg = trans_late('utils', "Passwords must be identical")
    if not passLong:
        msg = trans_late('utils', "Passwords must be greater than 8 characters long")
    if not (passLong or passEqual):
        msg = trans_late('utils', "Passwords must be identical and greater than 8 characters long")

    return msg


def password_transparency(encryption):
    if encryption != 'none':
        keyringClass = VortaKeyring.get_keyring().__class__.__name__
        messages = {
            'VortaDBKeyring': trans_late('utils', 'plaintext on disk.\nVorta supports the secure Secret Service API (Linux) and Keychain Access (macOS)'),  # noqa
            'VortaSecretStorageKeyring': trans_late('utils', 'the Secret Service API'),
            'VortaDarwinKeyring': trans_late('utils', 'Keychain Access'),
            'VortaKWallet5Keyring': trans_late('utils', 'KWallet 5'),
            'VortaMemoryKeyring': trans_late('utils', 'memory, and will be lost when Vorta is closed'),
            'VortaKWallet4Keyring': trans_late('utils', 'KWallet 4')
        }
        # Just in case some other keyring support is added
        keyringName = messages.get(keyringClass,
                                   trans_late('utils',
                                              'somewhere that was not anticipated. Please file a bug report on Github'))
        return trans_late('utils', 'The password will be stored in %s') % keyringName
    else:
        return ""    
