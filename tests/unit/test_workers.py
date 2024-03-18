import sys

from vorta.views.workers.file_path_info_worker import (
    get_path_datasize,
    normalize_path,
)


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
