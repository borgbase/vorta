import uuid

import pytest
from vorta.keyring.abc import VortaKeyring
from vorta.utils import (
    find_best_unit_for_sizes,
    pretty_bytes,
)


def test_keyring():
    UNICODE_PW = 'kjalsdfüadsfäadsfß'
    REPO = f'ssh://asdf123@vorta-test-repo.{uuid.uuid4()}.com/./repo'  # Random repo URL

    keyring = VortaKeyring.get_keyring()
    keyring.set_password('vorta-repo', REPO, UNICODE_PW)
    assert keyring.get_password("vorta-repo", REPO) == UNICODE_PW


@pytest.mark.parametrize(
    "precision, expected_unit",
    [
        (0, 1),  # return units as "1" (represents KB), min=100KB
        (1, 2),  # return units as "2" (represents MB), min=0.1MB
        (2, 2),  # still returns KB, since 0.1MB < min=0.001 GB to allow for GB to be best_unit
    ],
)
def test_best_unit_for_sizes_precision(precision, expected_unit):
    MB = 1000000
    sizes = [int(0.1 * MB), 100 * MB, 2000 * MB]
    best_unit = find_best_unit_for_sizes(sizes, metric=True, precision=precision)
    assert best_unit == expected_unit


@pytest.mark.parametrize(
    "sizes, expected_unit",
    [
        ([], 0),  # no sizes given but should still return "0" (represents bytes) as best representation
        ([102], 0),  # non-metric size 102 < 0.1KB (102 < 0.1 * 1024), so it will return 0 instead of 1
        ([103], 1),  # non-metric size 103 > 0.1KB (103 < 0.1 * 1024), so it will return 1
    ],
)
def test_best_unit_for_sizes_nonmetric(sizes, expected_unit):
    best_unit = find_best_unit_for_sizes(sizes, metric=False, precision=1)
    assert best_unit == expected_unit


@pytest.mark.parametrize(
    "size, metric, precision, fixed_unit, expected_output",
    [
        (10**5, True, 1, 2, "0.1 MB"),  # 100KB, metric, precision 1, fixed unit "2" (MB)
        (10**6, True, 0, 2, "1 MB"),  # 1MB, metric, precision 0, fixed unit "2" (MB)
        (10**6, True, 1, 2, "1.0 MB"),  # 1MB, metric, precision 1, fixed unit "2" (MB)
        (1024 * 1024, False, 1, 2, "1.0 MiB"),  # 1MiB, nonmetric, precision 1, fixed unit "2" (MiB)
    ],
)
def test_pretty_bytes_fixed_units(size, metric, precision, fixed_unit, expected_output):
    # test pretty bytes when specifying a fixed unit of measurement
    output = pretty_bytes(size, metric=metric, precision=precision, fixed_unit=fixed_unit)
    assert output == expected_output


@pytest.mark.parametrize(
    "size, metric, expected_output",
    [
        (10**6, True, "1.0 MB"),  # 1MB, metric
        (10**24, True, "1.0 YB"),  # 1YB, metric
        (10**30, True, "1000000.0 YB"),  # test huge number, metric
        (1024 * 1024, False, "1.0 MiB"),  # 1MiB, nonmetric
        (2**40 * 2**40, False, "1.0 YiB"),  # 1YiB, nonmetric
    ],
)
def test_pretty_bytes_nonfixed_units(size, metric, expected_output):
    # test pretty bytes when NOT specifying a fixed unit of measurement
    output = pretty_bytes(size, metric=metric, precision=1)
    assert output == expected_output
