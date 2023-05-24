import uuid

from vorta.keyring.abc import VortaKeyring
from vorta.utils import find_best_unit_for_sizes, pretty_bytes


def test_keyring():
    UNICODE_PW = 'kjalsdfüadsfäadsfß'
    REPO = f'ssh://asdf123@vorta-test-repo.{uuid.uuid4()}.com/./repo'  # Random repo URL

    keyring = VortaKeyring.get_keyring()
    keyring.set_password('vorta-repo', REPO, UNICODE_PW)
    assert keyring.get_password("vorta-repo", REPO) == UNICODE_PW


def test_best_size_unit_precision0():
    MB = 1000000
    sizes = [int(0.1 * MB), 100 * MB, 2000 * MB]
    unit = find_best_unit_for_sizes(sizes, metric=True, precision=0)
    assert unit == 1  # KB, min=100KB


def test_best_size_unit_precision1():
    MB = 1000000
    sizes = [int(0.1 * MB), 100 * MB, 2000 * MB]
    unit = find_best_unit_for_sizes(sizes, metric=True, precision=1)
    assert unit == 2  # MB, min=0.1MB


def test_best_size_unit_empty():
    sizes = []
    unit = find_best_unit_for_sizes(sizes, metric=True, precision=1)
    assert unit == 0  # bytes


def test_best_size_unit_precision3():
    MB = 1000000
    sizes = [1 * MB, 100 * MB, 2000 * MB]
    unit = find_best_unit_for_sizes(sizes, metric=True, precision=3)
    assert unit == 3  # GB, min=0.001 GB


def test_best_size_unit_nonmetric1():
    sizes = [102]
    unit = find_best_unit_for_sizes(sizes, metric=False, precision=1)
    assert unit == 0  # 102 < 0.1KB


def test_best_size_unit_nonmetric2():
    sizes = [103]
    unit = find_best_unit_for_sizes(sizes, metric=False, precision=1)
    assert unit == 1  # 103bytes == 0.1KB


def test_pretty_bytes_metric_fixed1():
    s = pretty_bytes(1000000, metric=True, precision=0, fixed_unit=2)
    assert s == "1 MB"


def test_pretty_bytes_metric_fixed2():
    s = pretty_bytes(1000000, metric=True, precision=1, fixed_unit=2)
    assert s == "1.0 MB"


def test_pretty_bytes_metric_fixed3():
    s = pretty_bytes(100000, metric=True, precision=1, fixed_unit=2)
    assert s == "0.1 MB"


def test_pretty_bytes_nonmetric_fixed1():
    s = pretty_bytes(1024 * 1024, metric=False, precision=1, fixed_unit=2)
    assert s == "1.0 MiB"


def test_pretty_bytes_metric_nonfixed2():
    s = pretty_bytes(1000000, metric=True, precision=1)
    assert s == "1.0 MB"


def test_pretty_bytes_metric_large():
    s = pretty_bytes(10**30, metric=True, precision=1)
    assert s == "1000000.0 YB"
