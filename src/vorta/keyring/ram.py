from .abc import VortaKeyring


class VortaMemoryKeyring(VortaKeyring):
    """
    Our own alternative fallback keyring service. Stores the
    passwords in RAM using a dictionary, and is lost on exit.
    """
    passwords = {}
    def set_password(self, service, repo_url, password):
        VortaMemoryKeyring.passwords[repo_url] = password

    def get_password(self, service, repo_url):
        return VortaMemoryKeyring.passwords.get(repo_url)

    @property
    def is_primary(self):
        return False
