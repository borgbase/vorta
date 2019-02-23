from .keyring_factory import VortaKeyring
import secretstorage


class VortaSecretStorageKeyring(VortaKeyring):
    """A wrapper for the secretstorage package to support the custom keyring backend"""

    def __init__(self):
        self.connection = secretstorage.dbus_init()

    def set_password(self, service, repo_url, password):
        collection = secretstorage.get_default_collection(self.connection)
        attributes = {'application': service, 'repo_url': repo_url}
        collection.create_item(f"vorta-{repo_url}", attributes, password, replace=True)

    def get_password(self, service, repo_url):
        collection = secretstorage.get_default_collection(self.connection)
        attributes = {'application': service, 'repo_url': repo_url}
        items = collection.search_items(attributes)
        return next(items).get_secret()
