from .keyring_backend import KeyringBackend


class VortaDBKeyring(KeyringBackend):
    """
    Our own fallback keyring service. Uses the main database
    to store repo passwords if no other (more secure) backend
    is available.
    """

    def set_password(self, service, repo_url, password):
        from .models import RepoPassword
        keyring_entry, created = RepoPassword.get_or_create(
            url=repo_url,
            defaults={'password': password}
        )
        keyring_entry.password = password
        keyring_entry.save()

    def get_password(self, service, repo_url):
        from .models import RepoPassword
        try:
            keyring_entry = RepoPassword.get(url=repo_url)
            return keyring_entry.password
        except Exception:
            return None

    def delete_password(self, service, repo_url):
        pass
