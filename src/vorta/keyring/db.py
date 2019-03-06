import peewee
from .abc import VortaKeyring


class VortaDBKeyring(VortaKeyring):
    """
    Our own fallback keyring service. Uses the main database
    to store repo passwords if no other (more secure) backend
    is available.
    """

    def set_password(self, service, repo_url, password):
        from vorta.models import RepoPassword
        keyring_entry, created = RepoPassword.get_or_create(
            url=repo_url,
            defaults={'password': password}
        )
        keyring_entry.password = password
        keyring_entry.save()

    def get_password(self, service, repo_url):
        from vorta.models import RepoPassword
        try:
            keyring_entry = RepoPassword.get(url=repo_url)
            return keyring_entry.password
        except peewee.DoesNotExist:
            return None

    @property
    def is_primary(self):
        return False
