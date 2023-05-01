import asyncio
import logging
import os

import secretstorage

from vorta.keyring.abc import VortaKeyring

logger = logging.getLogger(__name__)

LABEL_TEMPLATE = "Vorta Backup Repo {repo_url}"


class VortaSecretStorageKeyring(VortaKeyring):
    """A wrapper for the secretstorage package to support the custom keyring backend"""

    def __init__(self):
        """
        Test whether DBus and a SecretStorage provider are available.
        """
        try:
            self.connection = secretstorage.dbus_init()
        except secretstorage.exceptions.SecretServiceNotAvailableException as e:
            logger.debug("SecretStorage provider or DBus daemon is not available.")
            raise e
        asyncio.set_event_loop(asyncio.new_event_loop())
        self.collection = secretstorage.get_default_collection(self.connection)

    def set_password(self, service, repo_url, password):
        """
        Writes a password to the underlying store.
        """
        if self.is_unlocked:
            asyncio.set_event_loop(asyncio.new_event_loop())
            attributes = {
                'application': 'Vorta',
                'service': service,
                'repo_url': repo_url,
                'xdg:schema': 'org.freedesktop.Secret.Generic',
            }
            self.collection.create_item(
                LABEL_TEMPLATE.format(repo_url=repo_url),
                attributes,
                password,
                replace=True,
            )
            logger.debug(f"Saved password for repo {repo_url}")

    def get_password(self, service, repo_url):
        """
        Retrieve a password from the underlying store. Return None if not found.
        """
        if self.is_unlocked:
            asyncio.set_event_loop(asyncio.new_event_loop())
            attributes = {
                'application': 'Vorta',
                'service': service,
                'repo_url': repo_url,
            }
            items = list(self.collection.search_items(attributes))
            logger.debug('Found %i passwords matching repo URL.', len(items))
            if len(items) > 0:
                item = items[0]
                if item.is_locked() and item.unlock():
                    return None
                logger.debug(f"Retrieved password for repo {repo_url}")
                return item.get_secret().decode("utf-8")
        return None

    @property
    def is_unlocked(self):
        # unlock() will return True if the unlock prompt is dismissed
        return not (self.collection.is_locked() and self.collection.unlock())

    @classmethod
    def get_priority(cls):
        return 6 if "GNOME" in os.getenv("XDG_CURRENT_DESKTOP", "") else 5

    @property
    def is_system(self):
        return True
