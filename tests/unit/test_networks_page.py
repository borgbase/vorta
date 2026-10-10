from vorta.store.models import BackupProfileModel

PROFILE_NAME = 'Default'


def test_metered_checkbox_reflects_profile_on_load(qapp, window_load):
    window_load()
    checkbox = qapp.main_window.scheduleTab.networksPage.meteredNetworksCheckBox

    # init_db stores dont_run_on_metered_networks = False, so running on metered networks is allowed
    assert checkbox.isChecked()


def test_metered_checkbox_click_persists(qapp):
    page = qapp.main_window.scheduleTab.networksPage
    checkbox = page.meteredNetworksCheckBox

    profile = BackupProfileModel.get(name=PROFILE_NAME)
    profile.dont_run_on_metered_networks = True
    profile.save()
    checkbox.blockSignals(True)
    checkbox.setChecked(False)
    checkbox.blockSignals(False)

    checkbox.click()
    assert checkbox.isChecked()
    assert BackupProfileModel.get(name=PROFILE_NAME).dont_run_on_metered_networks is False

    checkbox.click()
    assert not checkbox.isChecked()
    assert BackupProfileModel.get(name=PROFILE_NAME).dont_run_on_metered_networks is True
