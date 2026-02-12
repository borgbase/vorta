import pytest

import vorta.borg
import vorta.store.models
from vorta.borg.key_import import BorgKeyImportJob
from vorta.utils import borg_compat


def test_key_import_prepare_v1(qapp, mocker):
    """Test that key import command is built correctly for Borg v1."""

    def mock_check(feature):
        if feature == 'V2':
            return False
        return True  # KEY_IMPORT is available

    mocker.patch.object(borg_compat, 'check', side_effect=mock_check)

    profile = vorta.store.models.BackupProfileModel.select().first()
    input_path = '/tmp/test_key.txt'

    params = BorgKeyImportJob.prepare(profile, input_path)

    assert params['ok']
    assert 'borg' in params['cmd']
    assert 'key' in params['cmd']
    assert 'import' in params['cmd']
    assert profile.repo.url in params['cmd']
    assert input_path in params['cmd']
    # V1 should not have --repo flag
    assert '--repo' not in params['cmd']


def test_key_import_prepare_v2(qapp, mocker):
    """Test that key import command is built correctly for Borg v2."""

    def mock_check(feature):
        # KEY_IMPORT and V2 should both return True
        return True

    mocker.patch.object(borg_compat, 'check', side_effect=mock_check)

    profile = vorta.store.models.BackupProfileModel.select().first()
    input_path = '/tmp/test_key.txt'

    params = BorgKeyImportJob.prepare(profile, input_path)

    assert params['ok']
    assert 'borg' in params['cmd']
    assert 'key' in params['cmd']
    assert 'import' in params['cmd']
    # V2 should have --repo flag followed by URL
    assert '--repo' in params['cmd']
    repo_idx = params['cmd'].index('--repo')
    assert params['cmd'][repo_idx + 1] == profile.repo.url
    assert input_path in params['cmd']


def test_key_import_no_paper_flag(qapp, mocker):
    """Test that key import doesn't expose --paper flag (interactive only)."""
    mocker.patch.object(borg_compat, 'check', return_value=True)

    profile = vorta.store.models.BackupProfileModel.select().first()
    input_path = '/tmp/test_key.txt'

    params = BorgKeyImportJob.prepare(profile, input_path)

    assert params['ok']
    # --paper should not be in the command
    assert '--paper' not in params['cmd']


def test_key_import_version_check(qapp, mocker):
    """Test that key import checks for minimum Borg version."""

    def mock_check(feature):
        if feature == 'KEY_IMPORT':
            return False  # Version too old
        return True

    mocker.patch.object(borg_compat, 'check', side_effect=mock_check)

    profile = vorta.store.models.BackupProfileModel.select().first()
    input_path = '/tmp/test_key.txt'

    params = BorgKeyImportJob.prepare(profile, input_path)

    assert not params['ok']
    assert 'message' in params
    assert 'Borg' in params['message']


def test_key_import_job_execution(qapp, qtbot, mocker, borg_json_output):
    """Test the full key import job execution."""
    stdout, stderr = borg_json_output('info')  # Reuse existing fixture output
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    profile = vorta.store.models.BackupProfileModel.select().first()
    input_path = '/tmp/test_key.txt'

    params = BorgKeyImportJob.prepare(profile, input_path)
    thread = BorgKeyImportJob(params['cmd'], params, profile.repo.id)

    with qtbot.waitSignal(thread.result, **pytest._wait_defaults) as blocker:
        blocker.connect(thread.updated)
        thread.run()

    assert blocker.args[0]['returncode'] == 0


def test_key_import_command_order_v1(qapp, mocker):
    """Test that v1 command has correct argument order."""

    def mock_check(feature):
        if feature == 'V2':
            return False
        return True

    mocker.patch.object(borg_compat, 'check', side_effect=mock_check)

    profile = vorta.store.models.BackupProfileModel.select().first()
    input_path = '/tmp/test_key.txt'

    params = BorgKeyImportJob.prepare(profile, input_path)
    cmd = params['cmd']

    # Expected order: borg key import [options] REPOSITORY PATH
    import_idx = cmd.index('import')
    repo_idx = cmd.index(profile.repo.url)
    path_idx = cmd.index(input_path)

    assert import_idx < repo_idx < path_idx


def test_key_import_command_order_v2(qapp, mocker):
    """Test that v2 command has correct argument order."""
    mocker.patch.object(borg_compat, 'check', return_value=True)

    profile = vorta.store.models.BackupProfileModel.select().first()
    input_path = '/tmp/test_key.txt'

    params = BorgKeyImportJob.prepare(profile, input_path)
    cmd = params['cmd']

    # Expected order: borg key import [options] --repo REPOSITORY PATH
    import_idx = cmd.index('import')
    repo_flag_idx = cmd.index('--repo')
    repo_url_idx = repo_flag_idx + 1
    path_idx = cmd.index(input_path)

    assert import_idx < repo_flag_idx < repo_url_idx < path_idx
    assert cmd[repo_url_idx] == profile.repo.url
