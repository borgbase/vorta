import pytest
from vorta.views.diff_result import parse_diff_lines


@pytest.mark.parametrize('line, expected', [
    ('changed link        some/changed/link',
     (0, 'changed', 'link', 'some/changed')),
    (' +77.8 kB  -77.8 kB some/changed/file',
     (77800, 'modified', 'file', 'some/changed')),
])
def test_parsing_diff_lines(line, expected):
    files_with_attributes, nested_file_list = parse_diff_lines([line])
    assert files_with_attributes == [expected]
