import sys

import pytest

from vorta.store.models import SettingsModel
from vorta.store.settings import get_grouped_checkbox_settings, get_misc_settings


def test_get_grouped_checkbox_settings_returns_groups_in_alphabetical_order():
    """Groups are non-empty and returned in ascending group-name order."""
    result = get_grouped_checkbox_settings()
    assert len(result) > 0

    group_names = [group_name for group_name, _ in result]
    assert group_names == sorted(group_names)

    for group_name, settings in result:
        assert isinstance(group_name, str) and group_name
        assert len(settings) > 0


def test_get_grouped_checkbox_settings_filters_legacy_keys():
    """A DB row whose key is not declared in get_misc_settings() must be dropped."""
    SettingsModel.create(
        key='fake_legacy_setting',
        label='Some Old Setting',
        value=True,
        type='checkbox',
        group='Misc',
    )

    all_keys = {s.key for _, settings in get_grouped_checkbox_settings() for s in settings}
    assert 'fake_legacy_setting' not in all_keys


@pytest.mark.skipif(sys.platform == 'darwin', reason="Updates group only filtered on non-darwin")
def test_get_grouped_checkbox_settings_skips_updates_on_non_darwin():
    """On non-darwin platforms the 'Updates' group is filtered out and must not appear."""
    SettingsModel.create(
        key='check_for_updates',
        label='Check for updates on startup',
        value=True,
        type='checkbox',
        group='Updates',
    )

    group_names = [name for name, _ in get_grouped_checkbox_settings()]
    assert 'Updates' not in group_names


def test_get_grouped_checkbox_settings_only_returns_declared_keys():
    """Every returned setting key must be present in get_misc_settings()."""
    declared = {entry['key'] for entry in get_misc_settings()}
    for _, settings in get_grouped_checkbox_settings():
        for setting in settings:
            assert setting.key in declared
