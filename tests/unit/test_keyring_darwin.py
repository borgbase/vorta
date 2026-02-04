import sys
import uuid

import pytest


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
def test_keyring_non_ascii_repo():
    from vorta.keyring.darwin import VortaDarwinKeyring

    UNICODE_PW = 'password'
    REPO = 'vorta-test-repo-한글'

    keyring = VortaDarwinKeyring()
    keyring.set_password('vorta-repo', REPO, UNICODE_PW)
    assert keyring.get_password("vorta-repo", REPO) == UNICODE_PW
