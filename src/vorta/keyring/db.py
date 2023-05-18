import logging

import peewee

from vorta.store.models import SettingsModel

from .abc import VortaKeyring

logger = logging.getLogger(__name__)


class VortaDBKeyring(VortaKeyring):
    """
    Our own fallback keyring service. Uses the main database
    to store repo passwords if no other (more secure) backend
    is available.
    """

    def set_password(self, service, repo_url, password):
        from vorta.store.models import RepoPassword

        keyring_entry, created = RepoPassword.get_or_create(url=repo_url, defaults={'password': password})
        keyring_entry.password = password
        keyring_entry.save()

        logger.debug(f"Saved password for repo {repo_url}")

    def get_password(self, service, repo_url):
        from vorta.store.models import RepoPassword

        try:
            keyring_entry = RepoPassword.get(url=repo_url)
            password = keyring_entry.password
            logger.debug(f"Retrieved password for repo {repo_url}")
            return password
        except peewee.DoesNotExist:
            return None

    @property
    def is_system(self):
        return False

    @property
    def is_unlocked(self):
        return True

    @classmethod
    def get_priority(cls):
        return 1 if SettingsModel.get(key='use_system_keyring').value else 10
