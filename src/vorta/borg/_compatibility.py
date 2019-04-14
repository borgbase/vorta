from pkg_resources import parse_version

MIN_BORG_FOR_FEATURE = {
    'BLAKE2': parse_version('1.1.4'),
    'ZSTD': parse_version('1.1.4'),
    # add new version-checks here.
}


class BorgCompatibility:
    """
    An internal class that keeps details of the Borg version
    in use and allows checking for specific features. Could be used
    to customize Borg commands by version in the future.
    """

    version = '0.0'
    path = ''

    def set_version(self, version, path):
        self.version = version
        self.path = path

    def check(self, feature_name):
        return parse_version(self.version) >= MIN_BORG_FOR_FEATURE[feature_name]
