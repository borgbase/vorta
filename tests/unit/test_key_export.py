import pytest

import vorta.borg
import vorta.store.models
from vorta.borg.key_export import BorgKeyExportJob
from vorta.utils import borg_compat


def test_key_export_prepare_v1(qapp, mocker):
    """Test that key export command is built correctly for Borg v1."""
    def mock_check(feature):
        if feature == 'V2':
            return False
        return True  # KEY_EXPORT is available
    
    mocker.patch.object(borg_compat, 'check', side_effect=mock_check)
    
    profile = vorta.store.models.BackupProfileModel.select().first()
    output_path = '/tmp/test_key.txt'
    
    params = BorgKeyExportJob.prepare(profile, output_path)
    
    assert params['ok']
    assert 'borg' in params['cmd']
    assert 'key' in params['cmd']
    assert 'export' in params['cmd']
    assert profile.repo.url in params['cmd']
    assert output_path in params['cmd']
    # V1 should not have --repo flag
    assert '--repo' not in params['cmd']


def test_key_export_prepare_v2(qapp, mocker):
    """Test that key export command is built correctly for Borg v2."""
    def mock_check(feature):
        # KEY_EXPORT and V2 should both return True
        return True
    
    mocker.patch.object(borg_compat, 'check', side_effect=mock_check)
    
    profile = vorta.store.models.BackupProfileModel.select().first()
    output_path = '/tmp/test_key.txt'
    
    params = BorgKeyExportJob.prepare(profile, output_path)
    
    assert params['ok']
    assert 'borg' in params['cmd']
    assert 'key' in params['cmd']
    assert 'export' in params['cmd']
    # V2 should have --repo flag followed by URL
    assert '--repo' in params['cmd']
    repo_idx = params['cmd'].index('--repo')
    assert params['cmd'][repo_idx + 1] == profile.repo.url
    assert output_path in params['cmd']


def test_key_export_with_paper_flag(qapp, mocker):
    """Test key export with --paper flag."""
    mocker.patch.object(borg_compat, 'check', return_value=True)
    
    profile = vorta.store.models.BackupProfileModel.select().first()
    output_path = '/tmp/test_key.txt'
    
    params = BorgKeyExportJob.prepare(profile, output_path, paper=True)
    
    assert params['ok']
    assert '--paper' in params['cmd']


def test_key_export_with_qr_html_flag(qapp, mocker):
    """Test key export with --qr-html flag."""
    mocker.patch.object(borg_compat, 'check', return_value=True)
    
    profile = vorta.store.models.BackupProfileModel.select().first()
    output_path = '/tmp/test_key.html'
    
    params = BorgKeyExportJob.prepare(profile, output_path, qr_html=True)
    
    assert params['ok']
    assert '--qr-html' in params['cmd']


def test_key_export_both_flags(qapp, mocker):
    """Test key export with both --paper and --qr-html flags."""
    mocker.patch.object(borg_compat, 'check', return_value=True)
    
    profile = vorta.store.models.BackupProfileModel.select().first()
    output_path = '/tmp/test_key.html'
    
    params = BorgKeyExportJob.prepare(profile, output_path, paper=True, qr_html=True)
    
    assert params['ok']
    assert '--paper' in params['cmd']
    assert '--qr-html' in params['cmd']


def test_key_export_job_execution(qapp, qtbot, mocker, borg_json_output):
    """Test the full key export job execution."""
    stdout, stderr = borg_json_output('info')  # Reuse existing fixture output
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)
    
    profile = vorta.store.models.BackupProfileModel.select().first()
    output_path = '/tmp/test_key.txt'
    
    params = BorgKeyExportJob.prepare(profile, output_path)
    thread = BorgKeyExportJob(params['cmd'], params, profile.repo.id)
    
    with qtbot.waitSignal(thread.result, **pytest._wait_defaults) as blocker:
        blocker.connect(thread.updated)
        thread.run()
    
    assert blocker.args[0]['returncode'] == 0
