"""Regression samples for Borg --log-json stderr (see borgbase/vorta#1354)."""

import json
from pathlib import Path

import pytest

_JSON_DIR = Path(__file__).resolve().parent / 'borg_json_output'


def _iter_ndjson_lines(relative_name: str):
    path = _JSON_DIR / relative_name
    text = path.read_text(encoding='utf-8')
    for line in text.splitlines():
        line = line.strip()
        if line:
            yield line


def test_borg_1_2_archive_progress_sample_is_valid_ndjson():
    lines = list(_iter_ndjson_lines('borg_1_2_archive_progress_stderr.json'))
    assert len(lines) == 8
    for line in lines:
        json.loads(line)


@pytest.mark.parametrize(
    'finished,expect_progress_line',
    [
        (False, True),
        (True, False),
        (None, True),
    ],
)
def test_archive_progress_emits_progress_only_when_not_finished(finished, expect_progress_line):
    """Mirrors ``borg_job.py``: progress for archive_progress only if not finished (Borg 1.2+)."""
    payload = {'type': 'archive_progress', 'nfiles': 1, 'original_size': 1, 'deduplicated_size': 0}
    if finished is not None:
        payload['finished'] = finished
    should_emit = not payload.get('finished', False)
    assert should_emit is expect_progress_line
