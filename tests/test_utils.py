import uuid
from vorta.keyring.abc import VortaKeyring


def test_keyring(qapp):
    UNICODE_PW = 'kjalsdfüadsfäadsfß'
    REPO = f'vorta-test-repo.{uuid.uuid4()}.com:repo'  # Random repo URL

    keyring = VortaKeyring.get_keyring()
    keyring.set_password('vorta-repo', REPO, UNICODE_PW)
    assert keyring.get_password("vorta-repo", REPO) == UNICODE_PW
