from pkg_resources import parse_version

MIN_BORG_FOR_FEATURE = {
    'BLAKE2': parse_version('1.1.4'),
    'ZSTD': parse_version('1.1.4'),
    'JSON_LOG': parse_version('1.1.0'),
    'DIFF_JSON_LINES': parse_version('1.1.16'),
    'DIFF_CONTENT_ONLY': parse_version('1.2.4'),
    'COMPACT_SUBCOMMAND': parse_version('1.2.0a1'),
    'V122': parse_version('1.2.2'),
    'V2': parse_version('2.0.0b1'),
    # add new version-checks here.
}


class BorgCompatibility:
    """
    An internal class that keeps details of the Borg version
    in use and allows checking for specific features. Could be used
    to customize Borg commands by version in the future.
    """

    version = '1.1.0'
    path = ''

    def set_version(self, version, path):
        self.version = version
        self.path = path

    def check(self, feature_name):
        return parse_version(self.version) >= MIN_BORG_FOR_FEATURE[feature_name]
