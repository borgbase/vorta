import sys
import uuid

import pytest
from PyQt6.QtWidgets import QWidget

from vorta.keyring.abc import VortaKeyring
from vorta.utils import (
    FilePathInfoAsync,
    choose_file_dialog,
    find_best_unit_for_sizes,
    get_path_datasize,
    is_system_tray_available,
    normalize_path,
    pretty_bytes,
    sort_sizes,
)


def test_keyring():
    UNICODE_PW = 'kjalsdfüadsfäadsfß'
    REPO = f'ssh://asdf123@vorta-test-repo.{uuid.uuid4()}.com/./repo'  # Random repo URL

    keyring = VortaKeyring.get_keyring()
    keyring.set_password('vorta-repo', REPO, UNICODE_PW)
    assert keyring.get_password("vorta-repo", REPO) == UNICODE_PW


@pytest.mark.parametrize(
    "input_sizes, expected_sorted",
    [
        # Basic ordering
        (["1.0 GB", "2.0 MB", "3.0 KB"], ["3.0 KB", "2.0 MB", "1.0 GB"]),
        # Multiple same units
        (["3.0 GB", "2.0 GB", "1.0 GB"], ["1.0 GB", "2.0 GB", "3.0 GB"]),
        # Multiple different units
        (["2.0 MB", "3.0 GB", "1.0 KB", "5.0 GB"], ["1.0 KB", "2.0 MB", "3.0 GB", "5.0 GB"]),
        # Larger to smaller units
        (["1.0 YB", "1.0 ZB", "1.0 EB", "1.0 PB"], ["1.0 PB", "1.0 EB", "1.0 ZB", "1.0 YB"]),
        # Skipping non-numeric sizes
        (["2x MB", "3.0 KB", "apple GB", "1.0 GB"], ["3.0 KB", "1.0 GB"]),
        # Skipping invalid suffix
        (["1.0 XX", "5.0 YY", "9.0 ZZ", "1.0 MB"], ["1.0 MB"]),
        # Floats with decimals
        (["2.5 GB", "2.3 GB", "1.1 MB"], ["1.1 MB", "2.3 GB", "2.5 GB"]),
        # Checking the same sizes across different units
        (["1.0 MB", "1000.0 KB"], ["1000.0 KB", "1.0 MB"]),
        # Handle empty lists
        ([], []),
    ],
)
def test_sort_sizes(input_sizes, expected_sorted):
    assert sort_sizes(input_sizes) == expected_sorted


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
    """
    Test pretty bytes when specifying a fixed unit of measurement
    """
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


def test_normalize_path():
    """
    Test that path is normalized for macOS, but does nothing for other platforms.
    """
    input_path = '/Users/username/caf\u00e9/file.txt'
    expected_output = '/Users/username/café/file.txt'

    actual_output = normalize_path(input_path)

    if sys.platform == 'darwin':
        assert actual_output == expected_output
    else:
        assert actual_output == input_path


def test_get_path_datasize(tmpdir):
    """
    Test that get_path_datasize() works correctly when passed excluded patterns.
    """
    # Create a temporary directory for testing
    test_dir = tmpdir.mkdir("test_dir")
    test_file = test_dir.join("test_file.txt")
    test_file.write("Hello, World!")

    # Create a subdirectory with a file to exclude
    excluded_dir = test_dir.mkdir("excluded_dir")
    excluded_file = excluded_dir.join("excluded_file.txt")
    excluded_file.write("Excluded file, should not be checked.")

    exclude_patterns = [f"{excluded_dir}"]

    # Test when the path is a directory
    data_size, files_count = get_path_datasize(str(test_dir), exclude_patterns)
    assert data_size == len("Hello, World!")
    assert files_count == 1

    # Test when the path is a file
    data_size, files_count = get_path_datasize(str(test_file), exclude_patterns)
    assert data_size == len("Hello, World!")
    assert files_count == 1

    # Test when the path is a directory with an excluded file
    data_size, files_count = get_path_datasize(str(excluded_dir), exclude_patterns)
    assert data_size == 0
    assert files_count == 0


PREFIXED_PATTERN_FILES = {
    'keep.txt': 'k',
    'a.pyc': 'pyc',
    'proj/node_modules/mod.js': 'module',
    'proj/src/app.py': 'app.py',
    'odd[1]*/inner.txt': 'literal',
    'odd1x/inner.txt': 'globbed',
    'cache/blob.bin': 'cacheblob',
    'cache2/blob.bin': 'cache2blob',
}


def make_pattern_tree(tmpdir):
    root = tmpdir.mkdir('root')
    for rel_path, content in PREFIXED_PATTERN_FILES.items():
        root.join(rel_path).write(content, ensure=True)
    return root


def expected_datasize(excluded):
    included = [content for path, content in PREFIXED_PATTERN_FILES.items() if path not in excluded]
    return sum(len(content) for content in included), len(included)


@pytest.mark.parametrize(
    'patterns, excluded',
    [
        (['fm:*/node_modules'], ['proj/node_modules/mod.js']),
        (['fm:*.pyc'], ['a.pyc']),
        (['pf:{root}/proj'], ['proj/node_modules/mod.js', 'proj/src/app.py']),
        (['pf:{root}/odd[1]*'], ['odd[1]*/inner.txt']),  # literal, so odd1x is kept
        (['pp:{root}/cache'], ['cache/blob.bin']),  # prefix ends at a path component, so cache2 is kept
        ([r're:\.(py|js)$'], ['proj/node_modules/mod.js', 'proj/src/app.py']),
        (['fm:*.pyc', 'pf:{root}/cache2'], ['a.pyc', 'cache2/blob.bin']),
        # ignored: sh: isn't supported by the estimate, unknown style, invalid regex
        (['sh:**/node_modules'], []),
        (['xx:*'], []),
        (['re:('], []),
    ],
)
def test_get_path_datasize_prefixed_patterns(tmpdir, patterns, excluded):
    """
    Test that get_path_datasize() handles borg's pattern style prefixes.
    """
    root = make_pattern_tree(tmpdir)
    exclude_patterns = [p.format(root=root) for p in patterns]

    assert get_path_datasize(str(root), exclude_patterns) == expected_datasize(excluded)


def test_file_path_info_ignores_comments(tmpdir):
    """
    Test that comment and empty lines of the exclusion string aren't used as patterns.
    """
    root = make_pattern_tree(tmpdir)
    exclude_str = f"# custom added rules\npf:{root}/proj\n\n# raw exclusions\n  # fm:*.pyc\nfm:*.pyc\n"

    file_info = FilePathInfoAsync(str(root), exclude_str)

    assert file_info.exclude_patterns == [f'pf:{root}/proj', 'fm:*.pyc']
    assert get_path_datasize(str(root), file_info.exclude_patterns) == expected_datasize(
        ['proj/node_modules/mod.js', 'proj/src/app.py', 'a.pyc']
    )


def test_is_system_tray_available(mocker):
    """
    Sanity check to ensure proper behavior
    """
    mocker.patch('PyQt6.QtWidgets.QSystemTrayIcon.isSystemTrayAvailable', return_value=False)
    assert is_system_tray_available() is False
    mocker.patch('PyQt6.QtWidgets.QSystemTrayIcon.isSystemTrayAvailable', return_value=True)
    assert is_system_tray_available() is True


def test_choose_file_dialog_sets_file_scheme_only(mocker, qapp):
    """Local path pickers must not offer unsupported schemes (borgbase/vorta#1631)."""
    mock_dialog = mocker.MagicMock()
    mocker.patch('vorta.utils.QFileDialog', return_value=mock_dialog)
    choose_file_dialog(QWidget(), 'Test')
    mock_dialog.setSupportedSchemes.assert_called_once_with(['file'])
