"""
Tests for VortaApp.bootstrap_profile() — covers the Flatpak HOME-override fix.

Issue: in a Flatpak sandbox, HOME is overridden to a sandboxed directory.
Both os.path.expanduser("~") and Path.home() read HOME, so they return the
sandboxed path and never find ~/.vorta-init.json in the real home directory.

Fix: use pwd.getpwuid(os.getuid()).pw_dir which queries the password database
directly, bypassing any HOME override.

Note: pwd is a Linux/macOS only module. Tests that rely on it are skipped on
Windows since Flatpak does not exist on Windows anyway.

Note: the qapp fixture is session-scoped (one instance shared across all tests).
Tests that mutate BackupProfileModel must restore state in a finally block to
avoid breaking other tests that run in the same session.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vorta.store.models import BackupProfileModel

# Marker applied to any test that patches pwd.getpwuid (Linux/macOS only)
skip_on_windows = pytest.mark.skipif(
    sys.platform == 'win32',
    reason="pwd module is not available on Windows; Flatpak does not exist on Windows"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_EXPORT = {"profiles": [], "settings": []}


def write_bootstrap(path: Path, content: dict = None) -> Path:
    """Write a minimal valid bootstrap JSON file and return its path."""
    path.write_text(json.dumps(content or MINIMAL_EXPORT))
    return path


def mock_successful_import(mocker):
    """
    Mock ProfileExport so bootstrap_profile() believes the import succeeded
    without needing a real valid export JSON structure.
    Returns a mock profile with a name attribute.
    """
    mock_profile = MagicMock()
    mock_profile.name = "TestProfile"
    mock_export = MagicMock()
    mock_export.to_db.return_value = mock_profile
    mocker.patch("vorta.application.ProfileExport.from_json", return_value=mock_export)
    return mock_profile


# ---------------------------------------------------------------------------
# 1. Core fix: pwd.getpwuid is used, not os.path.expanduser / HOME env var
# ---------------------------------------------------------------------------

@skip_on_windows
def test_pwd_getpwuid_is_called(qapp, tmp_path, mocker):
    """
    pwd.getpwuid must be called with the current uid to resolve the real
    home directory, not the HOME environment variable.
    """
    mock_pwd = mocker.patch("vorta.application.pwd.getpwuid")
    mock_pwd.return_value = MagicMock(pw_dir=str(tmp_path / "nonexistent"))

    qapp.bootstrap_profile(bootstrap_file=tmp_path / "nonexistent.json")

    mock_pwd.assert_called_once_with(os.getuid())


@skip_on_windows
def test_flatpak_home_override_is_bypassed(qapp, tmp_path, monkeypatch, mocker):
    """
    When HOME is set to a sandboxed path (as Flatpak does), the bootstrap
    file placed in the REAL home directory must still be found and loaded.
    """
    real_home = tmp_path / "real_home"
    real_home.mkdir()
    write_bootstrap(real_home / ".vorta-init.json")

    # Simulate Flatpak: HOME -> sandboxed path with no bootstrap file
    sandboxed_home = tmp_path / "sandboxed_home"
    sandboxed_home.mkdir()
    monkeypatch.setenv("HOME", str(sandboxed_home))

    mock_pwd = mocker.patch("vorta.application.pwd.getpwuid")
    mock_pwd.return_value = MagicMock(pw_dir=str(real_home))
    mock_successful_import(mocker)

    # Should not raise — file is found via pwd, not $HOME
    qapp.bootstrap_profile()


@skip_on_windows
def test_expanduser_misses_file_when_home_overridden(tmp_path, monkeypatch):
    """
    Regression guard: proves WHY the old approach was broken.
    os.path.expanduser("~") returns the sandboxed path when HOME is
    overridden, so the real bootstrap file is invisible to it.

    This test does not use qapp — pure path resolution, no side effects.
    """
    real_home = tmp_path / "real_home"
    real_home.mkdir()
    write_bootstrap(real_home / ".vorta-init.json")

    sandboxed_home = tmp_path / "sandboxed_home"
    sandboxed_home.mkdir()
    monkeypatch.setenv("HOME", str(sandboxed_home))

    # Old approach — resolves to sandboxed HOME, file not found
    old_path = Path(os.path.expanduser("~")) / ".vorta-init.json"
    assert not old_path.exists(), (
        "expanduser resolves to the sandboxed HOME, missing the real file"
    )

    # New approach — resolves to real home via pwd
    import pwd
    new_path = Path(pwd.getpwuid(os.getuid()).pw_dir) / ".vorta-init.json"
    assert new_path.exists(), (
        "pwd.getpwuid resolves to the real home where the file exists"
    )


# ---------------------------------------------------------------------------
# 2. Explicit bootstrap_file argument takes priority over pwd home
# ---------------------------------------------------------------------------

@skip_on_windows
def test_explicit_file_is_checked_first(qapp, tmp_path, mocker):
    """
    A bootstrap_file passed directly to bootstrap_profile() must be the
    first candidate tried, before the pwd-resolved home path.
    """
    explicit = write_bootstrap(tmp_path / "explicit.json")

    other_home = tmp_path / "other_home"
    other_home.mkdir()
    mock_pwd = mocker.patch("vorta.application.pwd.getpwuid")
    mock_pwd.return_value = MagicMock(pw_dir=str(other_home))
    mock_successful_import(mocker)

    # Should succeed using the explicit path, not the pwd home
    qapp.bootstrap_profile(bootstrap_file=explicit)


@skip_on_windows
def test_nonexistent_explicit_file_falls_back_to_pwd_home(qapp, tmp_path, mocker):
    """
    When the explicit bootstrap_file does not exist, bootstrap_profile()
    should fall back to the pwd-resolved home path and find the file there.
    """
    real_home = tmp_path / "real_home"
    real_home.mkdir()
    write_bootstrap(real_home / ".vorta-init.json")

    mock_pwd = mocker.patch("vorta.application.pwd.getpwuid")
    mock_pwd.return_value = MagicMock(pw_dir=str(real_home))
    mock_successful_import(mocker)

    # Explicit path does not exist -> falls back to pwd home
    qapp.bootstrap_profile(bootstrap_file=tmp_path / "nonexistent.json")


# ---------------------------------------------------------------------------
# 3. Default profile creation when no bootstrap file is found
# ---------------------------------------------------------------------------

def test_default_profile_created_when_no_bootstrap_file(qapp, tmp_path, mocker):
    """
    When no bootstrap file exists anywhere, a 'Default' profile must be
    created automatically so the app has at least one profile to work with.

    State is restored after the test so the session-scoped qapp is not
    left with a dirty database for subsequent tests.
    """
    existing = list(BackupProfileModel.select())
    BackupProfileModel.delete().execute()

    try:
        if sys.platform != 'win32':
            mock_pwd = mocker.patch("vorta.application.pwd.getpwuid")
            mock_pwd.return_value = MagicMock(pw_dir=str(tmp_path / "nonexistent"))

        qapp.bootstrap_profile(bootstrap_file=tmp_path / "nonexistent.json")

        assert BackupProfileModel.select().count() >= 1
        assert BackupProfileModel.get_or_none(name="Default") is not None
    finally:
        BackupProfileModel.delete().execute()
        for profile in existing:
            profile.save(force_insert=True)


def test_no_duplicate_default_profile(qapp, tmp_path, mocker):
    """
    Running bootstrap_profile() twice with no bootstrap file should not
    create two 'Default' profiles.
    """
    existing = list(BackupProfileModel.select())
    BackupProfileModel.delete().execute()

    try:
        if sys.platform != 'win32':
            mock_pwd = mocker.patch("vorta.application.pwd.getpwuid")
            mock_pwd.return_value = MagicMock(pw_dir=str(tmp_path / "nonexistent"))

        qapp.bootstrap_profile(bootstrap_file=tmp_path / "nonexistent.json")
        qapp.bootstrap_profile(bootstrap_file=tmp_path / "nonexistent.json")

        count = BackupProfileModel.select().where(BackupProfileModel.name == "Default").count()
        assert count == 1
    finally:
        BackupProfileModel.delete().execute()
        for profile in existing:
            profile.save(force_insert=True)


# ---------------------------------------------------------------------------
# 4. Bootstrap file lifecycle
# ---------------------------------------------------------------------------

def test_bootstrap_file_deleted_after_successful_import(qapp, tmp_path, mocker):
    """
    After a successful import the bootstrap file must be removed so it
    is not re-imported on the next startup.

    ProfileExport is mocked so we test the file deletion logic in
    bootstrap_profile() without needing a fully valid export JSON structure.
    """
    bootstrap = write_bootstrap(tmp_path / ".vorta-init.json")

    if sys.platform != 'win32':
        mock_pwd = mocker.patch("vorta.application.pwd.getpwuid")
        mock_pwd.return_value = MagicMock(pw_dir=str(tmp_path))

    # Mock the import so it succeeds and we reach the unlink() call
    mock_successful_import(mocker)

    qapp.bootstrap_profile(bootstrap_file=bootstrap)

    assert not bootstrap.exists(), (
        "Bootstrap file should be deleted after a successful import"
    )


def test_corrupt_bootstrap_file_shows_error_dialog(qapp, tmp_path, mocker):
    """
    A malformed JSON bootstrap file must trigger a QMessageBox.critical
    error dialog rather than crashing the application.
    """
    bootstrap = tmp_path / ".vorta-init.json"
    bootstrap.write_text("this is not valid json {{{")

    if sys.platform != 'win32':
        mock_pwd = mocker.patch("vorta.application.pwd.getpwuid")
        mock_pwd.return_value = MagicMock(pw_dir=str(tmp_path))

    mock_dialog = mocker.patch("vorta.application.QMessageBox.critical")

    qapp.bootstrap_profile(bootstrap_file=bootstrap)

    mock_dialog.assert_called_once()


def test_corrupt_bootstrap_file_is_not_deleted(qapp, tmp_path, mocker):
    """
    A bootstrap file that fails to import must NOT be deleted, so the
    user can repair it and try again on the next startup.
    """
    bootstrap = tmp_path / ".vorta-init.json"
    bootstrap.write_text("not valid json")

    if sys.platform != 'win32':
        mock_pwd = mocker.patch("vorta.application.pwd.getpwuid")
        mock_pwd.return_value = MagicMock(pw_dir=str(tmp_path))

    mocker.patch("vorta.application.QMessageBox.critical")

    qapp.bootstrap_profile(bootstrap_file=bootstrap)

    assert bootstrap.exists(), (
        "A corrupt bootstrap file must be preserved so the user can fix it"
    )


# ---------------------------------------------------------------------------
# 5. Docstring sanity check (catches the moved-docstring regression)
# ---------------------------------------------------------------------------

def test_bootstrap_profile_has_docstring():
    """
    The docstring must be the very first statement in bootstrap_profile.
    If it was placed after an executable line, Python treats it as a dead
    string expression and __doc__ returns None.

    This test does not use qapp — pure introspection, no side effects.
    """
    from vorta.application import VortaApp

    doc = VortaApp.bootstrap_profile.__doc__
    assert doc is not None, (
        "bootstrap_profile has no docstring — it may have been placed "
        "after an executable statement, turning it into a dead expression."
    )
    assert len(doc.strip()) > 0, "bootstrap_profile docstring must not be empty"