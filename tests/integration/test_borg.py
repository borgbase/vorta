"""
This file contains tests that directly call borg commands and verify the exit code.
"""

from pathlib import Path

import pytest
import vorta.borg
import vorta.store.models
from vorta.borg.info_archive import BorgInfoArchiveJob
from vorta.borg.info_repo import BorgInfoRepoJob
from vorta.borg.prune import BorgPruneJob


def test_borg_prune(qapp, qtbot):
    """This test runs borg prune on a test repo directly without UI"""
    params = BorgPruneJob.prepare(vorta.store.models.BackupProfileModel.select().first())
    thread = BorgPruneJob(params['cmd'], params, qapp)

    with qtbot.waitSignal(thread.result, **pytest._wait_defaults) as blocker:
        blocker.connect(thread.updated)
        thread.run()

    assert blocker.args[0]['returncode'] == 0


def test_borg_repo_info(qapp, qtbot, tmpdir):
    """This test runs borg info on a test repo directly without UI"""
    repo_info = {
        'repo_url': str(Path(tmpdir).parent / 'repo0'),
        'repo_name': 'repo0',
        'extra_borg_arguments': '',
        'ssh_key': '',
        'password': '',
    }

    params = BorgInfoRepoJob.prepare(repo_info)
    thread = BorgInfoRepoJob(params['cmd'], params, qapp)

    with qtbot.waitSignal(thread.result, **pytest._wait_defaults) as blocker:
        blocker.connect(thread.result)
        thread.run()

    assert blocker.args[0]['returncode'] == 0


def test_borg_archive_info(qapp, qtbot, archive_env):
    """Check that archive info command works"""
    params = BorgInfoArchiveJob.prepare(vorta.store.models.BackupProfileModel.select().first(), "test-archive1")
    thread = BorgInfoArchiveJob(params['cmd'], params, qapp)

    with qtbot.waitSignal(thread.result, **pytest._wait_defaults) as blocker:
        blocker.connect(thread.result)
        thread.run()

    assert blocker.args[0]['returncode'] == 0
