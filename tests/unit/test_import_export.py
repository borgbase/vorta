import copy
import json
import os
from pathlib import Path

import pytest
from PyQt6 import QtCore
from PyQt6.QtWidgets import QDialogButtonBox, QFileDialog, QMessageBox

import vorta.store.connection
from vorta.keyring.abc import VortaKeyring
from vorta.profile_export import ProfileExport, VersionException
from vorta.store.connection import DB
from vorta.store.models import (
    BackupProfileModel,
    ExclusionModel,
    RepoModel,
    RepoPassword,
    SettingsModel,
    SourceFileModel,
    WifiSettingModel,
)
from vorta.views.dialogs.profile.import_window import ImportWindow

VALID_IMPORT_FILE = Path(__file__).parent / 'profile_exports' / 'valid.json'
WIFI_IMPORT_FILE = Path(__file__).parent / 'profile_exports' / 'valid_with_wifi.json'
WIFI_PROFILE_NAME = 'Test Profile Wifi'
WIFI_FILE_RULES = {('HomeNet', True), ('CafeNet', False)}
ALL_SECTIONS = ('WifiSettingModel', 'ExclusionModel', 'SourceFileModel', 'SettingsModel')


@pytest.fixture
def mock_keyring(mocker):
    keyring = mocker.MagicMock()
    mocker.patch.object(VortaKeyring, 'get_keyring', return_value=keyring)
    return keyring


def load_export(path):
    return json.loads(Path(path).read_text())


def db_snapshot():
    def rows(model):
        return list(model.select().order_by(model.id).dicts())

    return {
        'repo': rows(RepoModel),
        'password': rows(RepoPassword),
        'source': rows(SourceFileModel),
        'exclusion': rows(ExclusionModel),
        'wifi': rows(WifiSettingModel),
        'profile': rows(BackupProfileModel),
        'settings': settings_snapshot(),
    }


def settings_snapshot():
    return sorted((s.key, s.value, s.str_value) for s in SettingsModel.select())


def wifi_rules(profile_id):
    return {(w.ssid, w.allowed) for w in WifiSettingModel.select().where(WifiSettingModel.profile == profile_id)}


def add_wifi_rule(profile, ssid, allowed=False):
    WifiSettingModel.create(ssid=ssid, allowed=allowed, profile=profile)


def set_setting(key, **values):
    SettingsModel.update(**values).where(SettingsModel.key == key).execute()


def get_setting(key):
    return SettingsModel.get(SettingsModel.key == key)


def make_target_profile():
    """A profile named like the Wi-Fi fixture, with its own Wi-Fi rule, exclusion and source."""
    profile = BackupProfileModel.create(name=WIFI_PROFILE_NAME, repo=RepoModel.get(id=1))
    add_wifi_rule(profile, 'TargetNet')
    ExclusionModel.create(profile=profile, name='*.target')
    SourceFileModel.create(profile=profile, dir='/target/source')
    return profile


def test_import_success(qapp, qtbot, rootdir, monkeypatch):
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: [VALID_IMPORT_FILE])
    monkeypatch.setattr(QMessageBox, 'information', lambda *args: None)

    main = qapp.main_window
    main.profile_import_action()
    import_dialog: ImportWindow = main.window
    import_dialog.overwriteExistingSettings.setChecked(True)

    qtbot.mouseClick(
        import_dialog.buttonBox.button(QDialogButtonBox.StandardButton.Ok), QtCore.Qt.MouseButton.LeftButton
    )
    qtbot.waitSignal(import_dialog.profile_imported, **pytest._wait_defaults)

    restored_profile = BackupProfileModel.get_or_none(name="Test Profile Restoration")
    assert restored_profile is not None

    restored_repo = restored_profile.repo
    assert restored_repo is not None
    assert len(SourceFileModel.select().where(SourceFileModel.profile == restored_profile)) == 3
    assert len(ExclusionModel.select().where(ExclusionModel.profile == restored_profile)) == 2


@pytest.mark.parametrize(
    "exception, error_message",
    [
        (AttributeError, "Schema upgrade failure"),
        (VersionException, "Newer profile_export export files cannot be used on older versions"),
        (PermissionError, "Cannot read profile_export export file due to permission error"),
        (FileNotFoundError, "Profile export file not found"),
    ],
)
def test_import_exceptions(qapp, qtbot, rootdir, monkeypatch, mocker, exception, error_message):
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: [VALID_IMPORT_FILE])
    monkeypatch.setattr(QMessageBox, 'information', lambda *args: None)

    main = qapp.main_window
    main.profile_import_action()
    import_dialog: ImportWindow = main.window
    import_dialog.overwriteExistingSettings.setChecked(True)

    def raise_exception(*args, **kwargs):
        raise exception

    # force an exception and mock the error QMessageBox
    monkeypatch.setattr(import_dialog.profile_export, 'to_db', raise_exception)
    mock_messagebox = mocker.patch.object(QMessageBox, "critical")

    qtbot.mouseClick(
        import_dialog.buttonBox.button(QDialogButtonBox.StandardButton.Ok), QtCore.Qt.MouseButton.LeftButton
    )

    # assert the correct error appears, and the profile does not get added
    mock_messagebox.assert_called_once()
    assert error_message in mock_messagebox.call_args[0][2]
    assert BackupProfileModel.get_or_none(name="Test Profile Restoration") is None


def test_import_bootstrap_success(qapp, mocker):
    mocked_unlink = mocker.MagicMock()
    mocker.patch.object(Path, 'unlink', mocked_unlink)
    qapp.bootstrap_profile(Path(VALID_IMPORT_FILE))

    assert mocked_unlink.called

    restored_profile = BackupProfileModel.get_or_none(name="Test Profile Restoration")
    assert restored_profile is not None

    restored_repo = restored_profile.repo
    assert restored_repo is not None

    assert len(SourceFileModel.select().where(SourceFileModel.profile == restored_profile)) == 3
    assert BackupProfileModel.select().count() == 2


@pytest.mark.parametrize(
    'content',
    [
        '{"SchemaVersion": {"version": 9999}}',
        'not json',
        '[]',
    ],
    ids=['newer-schema', 'invalid-json', 'not-an-object'],
)
def test_import_bootstrap_failure_no_profiles(qapp, mocker, tmp_path, window_load, content):
    bootstrap_file = tmp_path / '.vorta-init.json'
    bootstrap_file.write_text(content)
    critical = mocker.patch.object(QMessageBox, 'critical')
    pick = mocker.patch('vorta.application.VortaNotifications.pick')

    BackupProfileModel.delete().execute()
    assert BackupProfileModel.select().count() == 0

    qapp.bootstrap_profile(bootstrap_file)

    critical.assert_called_once()
    assert critical.call_args[0][1] == 'Failed to import profile'
    assert str(bootstrap_file) in critical.call_args[0][2]
    assert bootstrap_file.exists()
    pick.assert_not_called()
    # Must pass before window_load(): a failing MainWindow() leaves qapp without a main_window for later tests.
    assert [p.name for p in BackupProfileModel.select()] == ['Default']

    # Only the idle branch of build_menu() reads the profiles.
    mocker.patch.object(qapp.jobs_manager, 'is_worker_running', return_value=False)
    qapp.tray.build_menu()

    window_load()
    assert qapp.main_window.current_profile.name == 'Default'


def test_import_bootstrap_failure_existing_profile(qapp, mocker, tmp_path):
    bootstrap_file = tmp_path / '.vorta-init.json'
    bootstrap_file.write_text('{"SchemaVersion": {"version": 9999}}')
    critical = mocker.patch.object(QMessageBox, 'critical')
    pick = mocker.patch('vorta.application.VortaNotifications.pick')

    qapp.bootstrap_profile(bootstrap_file)

    critical.assert_called_once()
    assert bootstrap_file.exists()
    pick.assert_not_called()
    assert [p.name for p in BackupProfileModel.select()] == ['Default']


def test_import_fail_not_json(qapp, rootdir, monkeypatch):
    BAD_FILE = os.path.join(rootdir, 'profile_exports', 'invalid_no_json.json')

    def getOpenFileName(*args, **kwargs):
        return [BAD_FILE]

    monkeypatch.setattr(QFileDialog, "getOpenFileName", getOpenFileName)

    alert_message = None

    def critical(widget, title, message):
        nonlocal alert_message
        alert_message = message

    monkeypatch.setattr(QMessageBox, "critical", critical)

    main = qapp.main_window
    main.profile_import_action()

    # assert somehow that an alert is shown
    assert alert_message == 'This file does not contain valid JSON: Expecting value: line 1 column 1 (char 0)'


def test_export_success(qapp, qtbot, tmpdir, monkeypatch):
    FILE_PATH = os.path.join(tmpdir, "testresult.json")

    def getSaveFileName(*args, **kwargs):
        return [FILE_PATH]

    monkeypatch.setattr(QFileDialog, "getSaveFileName", getSaveFileName)

    main = qapp.main_window
    main.profile_export_action()
    export_dialog = main.window

    qtbot.mouseClick(
        export_dialog.buttonBox.button(QDialogButtonBox.StandardButton.Save), QtCore.Qt.MouseButton.LeftButton
    )
    qtbot.waitUntil(lambda: os.path.isfile(FILE_PATH))

    assert os.path.isfile(FILE_PATH)

    with open(FILE_PATH) as f:
        exported = json.load(f)
    assert 'ExclusionModel' in exported


def test_export_fail_unwritable(qapp, qtbot, monkeypatch):
    FILE_PATH = os.path.join(os.path.abspath(os.sep), "testresult.vortabackup")

    def getSaveFileName(*args, **kwargs):
        return [FILE_PATH]

    monkeypatch.setattr(QFileDialog, "getSaveFileName", getSaveFileName)

    alert_message = None

    def critical(widget, title, message):
        nonlocal alert_message
        alert_message = message

    monkeypatch.setattr(QMessageBox, "critical", critical)

    main = qapp.main_window
    main.profile_export_action()
    export_dialog = main.window

    qtbot.mouseClick(
        export_dialog.buttonBox.button(QDialogButtonBox.StandardButton.Save), QtCore.Qt.MouseButton.LeftButton
    )

    assert 'could not be created' in alert_message
    assert not os.path.isfile(FILE_PATH)


def test_import_rollback_on_unknown_key(qapp, mock_keyring):
    data = load_export(VALID_IMPORT_FILE)
    data['repo']['url'] = '/tmp/vorta-rollback-repo'
    data['no_such_field'] = 'x'
    export = ProfileExport(data)
    original = copy.deepcopy(data)
    before = db_snapshot()

    with pytest.raises(AttributeError):
        export.to_db(overwrite_settings=True)

    assert db_snapshot() == before
    mock_keyring.set_password.assert_not_called()
    assert export._profile_dict == original


def test_import_rollback_mid_transaction(qapp, mock_keyring, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError('insert failed')

    monkeypatch.setattr(ExclusionModel, 'insert_many', fail)
    before = db_snapshot()

    with pytest.raises(RuntimeError):
        ProfileExport(load_export(VALID_IMPORT_FILE)).to_db(overwrite_settings=True)

    assert db_snapshot() == before
    assert (
        not BackupProfileModel.select().where(BackupProfileModel.name.startswith('Test Profile Restoration')).exists()
    )
    mock_keyring.set_password.assert_not_called()


def test_import_dialog_schema_failure_rolls_back(qapp, qtbot, tmp_path, monkeypatch, mocker, mock_keyring):
    data = load_export(VALID_IMPORT_FILE)
    data['repo']['url'] = '/tmp/vorta-dialog-rollback-repo'
    data['no_such_field'] = 'x'
    bad_file = tmp_path / 'bad_key.json'
    bad_file.write_text(json.dumps(data))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: [str(bad_file)])
    mock_messagebox = mocker.patch.object(QMessageBox, "critical")

    main = qapp.main_window
    main.profile_import_action()
    import_dialog: ImportWindow = main.window
    import_dialog.overwriteExistingSettings.setChecked(True)
    before = db_snapshot()

    qtbot.mouseClick(
        import_dialog.buttonBox.button(QDialogButtonBox.StandardButton.Ok), QtCore.Qt.MouseButton.LeftButton
    )

    mock_messagebox.assert_called_once()
    assert "Schema upgrade failure" in mock_messagebox.call_args[0][2]
    assert db_snapshot() == before
    mock_keyring.set_password.assert_not_called()


def test_import_wifi_remapped_to_new_profile(qapp, mock_keyring):
    other = BackupProfileModel.get(id=1)
    add_wifi_rule(other, 'OtherNet')

    new_profile = ProfileExport(load_export(WIFI_IMPORT_FILE)).to_db(overwrite_settings=True)

    assert new_profile.id != 1
    assert wifi_rules(new_profile.id) == WIFI_FILE_RULES
    assert wifi_rules(other.id) == {('OtherNet', False)}


def test_import_wifi_overwrite_profile(qapp, mock_keyring):
    other = BackupProfileModel.get(id=1)
    add_wifi_rule(other, 'OtherNet')
    target = make_target_profile()

    new_profile = ProfileExport(load_export(WIFI_IMPORT_FILE)).to_db(overwrite_profile=True, overwrite_settings=True)

    assert new_profile.id == target.id
    assert wifi_rules(target.id) == WIFI_FILE_RULES
    assert wifi_rules(other.id) == {('OtherNet', False)}


def test_import_wifi_without_overwrite_settings(qapp, mock_keyring):
    before = settings_snapshot()

    new_profile = ProfileExport(load_export(WIFI_IMPORT_FILE)).to_db(overwrite_settings=False)

    assert wifi_rules(new_profile.id) == WIFI_FILE_RULES
    assert settings_snapshot() == before


def strip_sections(data, *keys):
    for key in keys:
        del data[key]
    return data


@pytest.mark.parametrize('overwrite_settings', [True, False])
def test_import_absent_sections_overwrite_keeps_target_rows(qapp, mock_keyring, overwrite_settings):
    target = make_target_profile()
    before = settings_snapshot()

    data = strip_sections(load_export(WIFI_IMPORT_FILE), *ALL_SECTIONS)
    new_profile = ProfileExport(data).to_db(overwrite_profile=True, overwrite_settings=overwrite_settings)

    assert new_profile.id == target.id
    assert wifi_rules(target.id) == {('TargetNet', False)}
    assert [e.name for e in ExclusionModel.select().where(ExclusionModel.profile == target.id)] == ['*.target']
    assert [s.dir for s in SourceFileModel.select().where(SourceFileModel.profile == target.id)] == ['/target/source']
    assert settings_snapshot() == before


@pytest.mark.parametrize('overwrite_settings', [True, False])
def test_import_absent_sections_as_new(qapp, mock_keyring, overwrite_settings):
    data = strip_sections(load_export(WIFI_IMPORT_FILE), 'WifiSettingModel', 'ExclusionModel', 'SettingsModel')
    new_profile = ProfileExport(data).to_db(overwrite_settings=overwrite_settings)

    assert new_profile.name == WIFI_PROFILE_NAME
    assert SourceFileModel.select().where(SourceFileModel.profile == new_profile.id).count() == 1
    assert wifi_rules(new_profile.id) == set()


def test_import_new_profile_does_not_inherit_orphan_rows(qapp, mock_keyring):
    """Rows left under a free profile id, e.g. by an older failed import, must not attach to a new profile."""
    data = strip_sections(load_export(WIFI_IMPORT_FILE), *ALL_SECTIONS)
    data['id'] = 7
    WifiSettingModel.insert(ssid='OrphanNet', allowed=False, profile=7).execute()
    SourceFileModel.insert(dir='/orphan/source', profile=7).execute()
    ExclusionModel.insert(name='*.orphan', profile=7).execute()

    new_profile = ProfileExport(data).to_db()

    assert new_profile.id == 7
    assert wifi_rules(7) == set()
    assert not SourceFileModel.select().where(SourceFileModel.profile == 7).exists()
    assert not ExclusionModel.select().where(ExclusionModel.profile == 7).exists()


def test_import_settings_merge(qapp, mock_keyring):
    set_setting('enable_fixed_units', value=True)  # not in the file, non-default locally
    set_setting('enable_notifications', value=True)  # file has False
    set_setting('enable_notifications_success', value=False)
    window_width = get_setting('previous_window_width').str_value
    use_system_keyring = get_setting('use_system_keyring').value

    data = load_export(WIFI_IMPORT_FILE)
    data['SettingsModel'] += [
        {'key': 'no_such_setting', 'value': True, 'str_value': '', 'label': 'Unknown', 'type': 'checkbox'},
        {'key': 'previous_window_width', 'value': False, 'str_value': '1234', 'label': 'x', 'type': 'internal'},
        {'key': 'use_system_keyring', 'value': not use_system_keyring, 'str_value': ''},
        {'key': 'enable_notifications_success', 'value': True},
    ]
    ProfileExport(data).to_db(overwrite_settings=True)

    assert get_setting('enable_fixed_units').value is True
    assert get_setting('enable_notifications').value is False
    assert get_setting('enable_notifications_success').value is True
    assert SettingsModel.get_or_none(SettingsModel.key == 'no_such_setting') is None
    assert get_setting('previous_window_width').str_value == window_width
    assert get_setting('use_system_keyring').value == use_system_keyring


def test_import_autostart_applied(qapp, mock_keyring, mocker, monkeypatch):
    """Guard for #1092: an imported autostart value must reach the autostart hook."""
    set_setting('autostart', value=False)
    autostart_hook = mocker.MagicMock()
    monkeypatch.setattr(vorta.store.connection, 'open_app_at_startup', autostart_hook)

    data = load_export(WIFI_IMPORT_FILE)
    data['SettingsModel'].append(
        {'key': 'autostart', 'value': True, 'str_value': '', 'label': 'Autostart', 'type': 'checkbox'}
    )
    ProfileExport(data).to_db(overwrite_settings=True)

    assert get_setting('autostart').value is True
    autostart_hook.assert_called_with(True)


def test_import_password_written_after_commit(qapp, mock_keyring):
    in_transaction = []

    def record_state(service, url, password):
        in_transaction.append(DB.in_transaction())
        assert BackupProfileModel.get_or_none(name='Test Profile Restoration') is not None

    mock_keyring.set_password.side_effect = record_state

    ProfileExport(load_export(VALID_IMPORT_FILE)).to_db(overwrite_settings=True)

    mock_keyring.set_password.assert_called_once_with('vorta-repo', '/tmp/asdf', 'Tr0ub4dor&3')
    assert in_transaction == [False]


def test_import_takes_write_lock_upfront(qapp, mock_keyring, mocker):
    """A deferred transaction fails with 'database is locked' if another thread writes after our first read."""
    begin = mocker.spy(DB.obj, 'begin')

    ProfileExport(load_export(VALID_IMPORT_FILE)).to_db()

    begin.assert_called_once_with('IMMEDIATE')


def test_export_import_round_trip(qapp, mock_keyring, tmp_path):
    mock_keyring.get_password.return_value = 'round-trip-secret'
    profile = BackupProfileModel.get(id=1)
    add_wifi_rule(profile, 'RoundTripNet')
    SourceFileModel.create(profile=profile, dir='/round/trip')
    ExclusionModel.create(profile=profile, name='*.roundtrip')
    exported = tmp_path / 'export.json'
    exported.write_text(ProfileExport.from_db(profile).to_json())
    before = settings_snapshot()

    new_profile = ProfileExport.from_json(exported).to_db()

    assert new_profile.id != profile.id
    assert new_profile.name == f'{profile.name}-1'
    assert new_profile.repo.url == profile.repo.url
    assert wifi_rules(new_profile.id) == wifi_rules(profile.id) == {('RoundTripNet', False)}
    for model in (SourceFileModel, ExclusionModel):
        assert model.select().where(model.profile == new_profile.id).count() == (
            model.select().where(model.profile == profile.id).count()
        )
    assert settings_snapshot() == before
    mock_keyring.set_password.assert_called_once_with('vorta-repo', profile.repo.url, 'round-trip-secret')


def test_import_password_failure_keeps_profile(qapp, mock_keyring):
    mock_keyring.set_password.side_effect = RuntimeError('keyring unavailable')

    new_profile = ProfileExport(load_export(VALID_IMPORT_FILE)).to_db(overwrite_settings=True)

    assert BackupProfileModel.get_or_none(id=new_profile.id) is not None
    assert SourceFileModel.select().where(SourceFileModel.profile == new_profile.id).count() == 3


def test_export_wifi_without_id(qapp, mock_keyring):
    profile = BackupProfileModel.get(id=1)
    add_wifi_rule(profile, 'ExportNet')

    exported = ProfileExport.from_db(profile, store_password=False)._profile_dict

    assert [w['ssid'] for w in exported['WifiSettingModel']] == ['ExportNet']
    assert all('id' not in w for w in exported['WifiSettingModel'])
