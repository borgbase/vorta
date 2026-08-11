import sys

from vorta.borg import fuse_venv
from vorta.borg.borg_job import BorgJob
from vorta.borg.mount import BorgMountJob
from vorta.store.models import SettingsModel
from vorta.store.settings import get_misc_settings


def set_use_venv(value):
    setting, _ = SettingsModel.get_or_create(
        key='use_managed_mount_venv',
        defaults={
            'label': 'Use managed Python environment for mounting',
            'type': 'checkbox',
            'value': False,
        },
    )
    setting.value = value
    setting.save()


def test_setting_only_declared_on_darwin(monkeypatch):
    monkeypatch.setattr(sys, 'platform', 'darwin')
    assert 'use_managed_mount_venv' in {s['key'] for s in get_misc_settings()}

    monkeypatch.setattr(sys, 'platform', 'linux')
    assert 'use_managed_mount_venv' not in {s['key'] for s in get_misc_settings()}


def test_mount_uses_venv_borg_when_enabled_and_ready(monkeypatch):
    set_use_venv(True)
    monkeypatch.setattr(fuse_venv, 'is_supported', lambda: True)
    monkeypatch.setattr(fuse_venv, 'is_venv_ready', lambda: True)

    assert BorgMountJob.prepare_bin() == str(fuse_venv.venv_borg_bin())


def test_mount_falls_back_when_venv_not_ready(monkeypatch):
    set_use_venv(True)
    monkeypatch.setattr(fuse_venv, 'is_supported', lambda: True)
    monkeypatch.setattr(fuse_venv, 'is_venv_ready', lambda: False)

    assert BorgMountJob.prepare_bin() == BorgJob.prepare_bin()


def test_mount_uses_default_borg_when_disabled(monkeypatch):
    set_use_venv(False)
    monkeypatch.setattr(fuse_venv, 'is_supported', lambda: True)
    monkeypatch.setattr(fuse_venv, 'is_venv_ready', lambda: True)

    assert BorgMountJob.prepare_bin() == BorgJob.prepare_bin()


def test_other_jobs_unaffected(monkeypatch):
    """Enabling the venv must never change binary resolution for non-mount jobs."""
    from vorta.borg.create import BorgCreateJob

    set_use_venv(True)
    monkeypatch.setattr(fuse_venv, 'is_supported', lambda: True)
    monkeypatch.setattr(fuse_venv, 'is_venv_ready', lambda: True)

    assert BorgCreateJob.prepare_bin.__func__ is BorgJob.prepare_bin.__func__
    assert BorgCreateJob.prepare_bin() != str(fuse_venv.venv_borg_bin())
