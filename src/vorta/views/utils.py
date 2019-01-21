from peewee import Proxy
from vorta.models import SettingsModel


def get_icon_class():
    """
    Choose a package to import collection_rc from.

    light = white icons, dark = black icons.

    Defaults to dark icons (light theme) if DB isn't initialized yet.
    """
    if SettingsModel._meta.database.obj is None:
        return 'vorta.views.dark'
    else:
        use_light_icon = SettingsModel.get(key='use_light_icon').value
        return 'vorta.views.light' if use_light_icon else 'vorta.views.dark'
