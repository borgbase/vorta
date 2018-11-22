import sentry_sdk
from vorta._version import __version__


def scrub_sensitive_data(event, hint):
    """Adapted from https://stackoverflow.com/questions/9807634/
            find-all-occurrences-of-a-key-in-nested-python-dictionaries-and-lists/29652561"""
    def gen_dict_extract(key, var):
        if hasattr(var, 'items'):
            for k, v in var.items():
                if k == key:
                    var[k] = 'FILTERED'
                    yield v
                if isinstance(v, dict):
                    for result in gen_dict_extract(key, v):
                        yield result
                elif isinstance(v, list):
                    for d in v:
                        for result in gen_dict_extract(key, d):
                            yield result

    list(gen_dict_extract('BORG_PASSPHRASE', event))
    list(gen_dict_extract('password', event))
    return event


def init():
    sentry_sdk.init("https://a4a23df3e44743d5b5c5f06417a9a809@sentry.io/1311799",
                    release=__version__,
                    before_send=scrub_sensitive_data)
