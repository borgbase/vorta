from packaging.version import Version

MIN_BORG_FOR_FEATURE = {
    "BLAKE2": Version("1.1.4"),
    "ZSTD": Version("1.1.4"),
    "JSON_LOG": Version("1.1.0"),
    "DIFF_JSON_LINES": Version("1.1.16"),
    "COMPACT_SUBCOMMAND": Version("1.2.0a1"),
    "V122": Version("1.2.2"),
    "V2": Version("2.0.0b10"),
    'CHANGE_PASSPHRASE': Version('1.1.0'),
    # add new version-checks here.
}


class BorgCompatibility:
    """
    An internal class that keeps details of the Borg version
    in use and allows checking for specific features. Could be used
    to customize Borg commands by version in the future.
    """

    version = "1.1.4"
    path = ""

    def set_version(self, version, path):
        self.version = version
        self.path = path

    def check(self, feature_name):
        return Version(self.version) >= MIN_BORG_FOR_FEATURE[feature_name]

    def get_version(self):
        """Returns the version and path of the Borg binary."""
        return self.version, self.path
