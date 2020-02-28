import uuid
from vorta.utils import keyring


def test_keyring(qapp):
    UNICODE_PW = 'kjalsdfüadsfäadsfß'
    REPO = f'vorta-test-repo.{uuid.uuid4()}.com:repo'  # Random repo URL

    keyring.set_password('vorta-repo', REPO, UNICODE_PW)
    assert keyring.get_password("vorta-repo", REPO) == UNICODE_PW
