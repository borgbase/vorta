import uuid
from vorta.keyring.abc import get_keyring


def test_keyring(qapp):
    UNICODE_PW = 'kjalsdfüadsfäadsfß'
    REPO = f'vorta-test-repo.{uuid.uuid4()}.com:repo'  # Random repo URL

    get_keyring().set_password('vorta-repo', REPO, UNICODE_PW)
    assert get_keyring().get_password("vorta-repo", REPO) == UNICODE_PW
