import secretstorage
import asyncio
from vorta.keyring.abc import VortaKeyring
from vorta.log import logger


class VortaSecretStorageKeyring(VortaKeyring):
    """A wrapper for the secretstorage package to support the custom keyring backend"""

    def __init__(self):
        """
        Test whether DBus and Gnome-Keyring are available.
        """
        self.connection = secretstorage.dbus_init()
        asyncio.set_event_loop(asyncio.new_event_loop())
        secretstorage.get_default_collection(self.connection)

    def set_password(self, service, repo_url, password):
        asyncio.set_event_loop(asyncio.new_event_loop())
        collection = secretstorage.get_default_collection(self.connection)
        attributes = {
            'application': 'Vorta',
            'service': service,
            'repo_url': repo_url,
            'xdg:schema': 'org.freedesktop.Secret.Generic'}
        collection.create_item(repo_url, attributes, password, replace=True)

    def get_password(self, service, repo_url):
        asyncio.set_event_loop(asyncio.new_event_loop())
        collection = secretstorage.get_default_collection(self.connection)
        if collection.is_locked():
            collection.unlock()
        attributes = {'application': 'Vorta', 'service': service, 'repo_url': repo_url}
        items = list(collection.search_items(attributes))
        logger.debug('Found %i passwords matching repo URL.', len(items))
        if len(items) > 0:
            return items[0].get_secret().decode("utf-8")
        return None
