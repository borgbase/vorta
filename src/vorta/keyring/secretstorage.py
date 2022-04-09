import asyncio
import os
import sys

import secretstorage

from vorta.keyring.abc import VortaKeyring
from vorta.log import logger

LABEL_TEMPLATE = "Vorta Backup Repo {repo_url}"


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
        """
        Writes a password to the underlying store.
        """
        try:
            asyncio.set_event_loop(asyncio.new_event_loop())
            collection = secretstorage.get_default_collection(self.connection)
            attributes = {
                'application': 'Vorta',
                'service': service,
                'repo_url': repo_url,
                'xdg:schema': 'org.freedesktop.Secret.Generic'}
            collection.create_item(LABEL_TEMPLATE.format(repo_url=repo_url),
                                   attributes,
                                   password,
                                   replace=True)
        except secretstorage.exceptions.ItemNotFoundException:
            logger.error("SecretStorage writing failed", exc_info=sys.exc_info())

    def get_password(self, service, repo_url):
        """
        Retrieve a password from the underlying store. Return None if not found.
        """
        if self.is_unlocked:
            asyncio.set_event_loop(asyncio.new_event_loop())
            collection = secretstorage.get_default_collection(self.connection)
            attributes = {'application': 'Vorta', 'service': service, 'repo_url': repo_url}
            items = list(collection.search_items(attributes))
            logger.debug('Found %i passwords matching repo URL.', len(items))
            if len(items) > 0:
                item = items[0]
                if item.is_locked():  # Some providers lock items until the user manually approves it
                    item.unlock()
                return item.get_secret().decode("utf-8")
        return None

    @property
    def is_unlocked(self):
        try:
            collection = secretstorage.get_default_collection(self.connection)
            if collection.is_locked():  # Prompt for unlock
                collection.unlock()
            return not collection.is_locked()  # In case of denial
        except secretstorage.exceptions.SecretServiceNotAvailableException:
            logger.debug('SecretStorage is closed.')
            return False

    @classmethod
    def get_priority(cls):
        return 6 if "GNOME" in os.getenv("XDG_CURRENT_DESKTOP", "") else 5

    @property
    def is_system(self):
        return True
