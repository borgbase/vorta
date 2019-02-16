from .keyring_backend import KeyringBackend
import secretstorage

class VortaSecretStorageKeyring(KeyringBackend):
    """A wrapper for the secretstorage package to support the custom keyring backend"""

    def set_password(self, service, repo_url, password):
        connection = secretstorage.dbus_init()
        collection = secretstorage.get_default_collection(connection)
        attributes = {'application': service, 'repo_url': repo_url}
        collection.create_item(f"vorta-{repo_url}", attributes, password.encode(), replace=True)

    def get_password(self, service, repo_url):
        connection = secretstorage.dbus_init()
        collection = secretstorage.get_default_collection(connection)
        attributes = {'application': service, 'repo_url': repo_url}
        try:
            items = collection.search_items(attributes)
            return next(items).get_secret().decode()
        except Exception:
            return None
