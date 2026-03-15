from types import SimpleNamespace

import pytest
from PyQt6.QtWidgets import QWidget

from vorta.store.models import BackupProfileModel, RepoModel
from vorta.views.base_tab import BaseTab


class FakeSignal:
    def __init__(self):
        self._slots = []

    def connect(self, slot):
        self._slots.append(slot)
        return slot

    def disconnect(self, slot):
        self._slots.remove(slot)

    def emit(self, *args, **kwargs):
        for slot in list(self._slots):
            try:
                slot(*args, **kwargs)
            except TypeError:
                slot()


class DummyTab(BaseTab, QWidget):
    def __init__(self, parent=None, profile_provider=None):
        super().__init__(parent=parent, profile_provider=profile_provider)
        self.profile_change_count = 0
        self.palette_change_count = 0
        self.backup_finished_count = 0
        self.populate_count = 0

    def on_profile_change(self):
        self.profile_change_count += 1

    def on_palette_change(self):
        self.palette_change_count += 1

    def on_backup_finished(self):
        self.backup_finished_count += 1

    def populate_from_profile(self):
        self.populate_count += 1


def test_base_tab_uses_injected_profile_provider(qapp):
    repo = RepoModel.get(id=1)
    injected_profile = BackupProfileModel.create(name='Injected', repo=repo.id)

    tab = DummyTab(profile_provider=lambda: BackupProfileModel.get(id=injected_profile.id))

    assert tab.profile().id == injected_profile.id

    tab.save_profile_attr('compression', 'none')
    assert BackupProfileModel.get(id=injected_profile.id).compression == 'none'

    tab.save_repo_attr('name', 'Injected Repo')
    assert RepoModel.get(id=repo.id).name == 'Injected Repo'


def test_base_tab_cleans_up_tracked_connections(qapp):
    profile = BackupProfileModel.get(id=1)
    tab = DummyTab(profile_provider=lambda: BackupProfileModel.get(id=profile.id))
    fake_app = SimpleNamespace(
        profile_changed_event=FakeSignal(),
        paletteChanged=FakeSignal(),
        backup_finished_event=FakeSignal(),
    )
    tab.app = fake_app
    tab.track_profile_change(tab.on_profile_change)
    tab.track_palette_change(tab.on_palette_change)
    tab.track_backup_finished(tab.on_backup_finished)

    fake_app.profile_changed_event.emit()
    fake_app.paletteChanged.emit(qapp.palette())
    fake_app.backup_finished_event.emit({})
    assert tab.profile_change_count == 1
    assert tab.palette_change_count == 1
    assert tab.backup_finished_count == 1

    tab._cleanup_tracked_connections()
    fake_app.profile_changed_event.emit()
    fake_app.paletteChanged.emit(qapp.palette())
    fake_app.backup_finished_event.emit({})
    assert tab.profile_change_count == 1
    assert tab.palette_change_count == 1
    assert tab.backup_finished_count == 1


def test_base_tab_track_methods_support_call_now(qapp):
    profile = BackupProfileModel.get(id=1)
    tab = DummyTab(profile_provider=lambda: BackupProfileModel.get(id=profile.id))
    fake_app = SimpleNamespace(
        profile_changed_event=FakeSignal(),
        paletteChanged=FakeSignal(),
        backup_finished_event=FakeSignal(),
    )
    tab.app = fake_app

    tab.track_profile_change(call_now=True)
    tab.track_palette_change(tab.on_palette_change, call_now=True)
    tab.track_backup_finished(tab.on_backup_finished, call_now=True)

    assert tab.populate_count == 1
    assert tab.palette_change_count == 1
    assert tab.backup_finished_count == 1


def test_base_tab_bind_attr_helpers_update_models(qapp):
    repo = RepoModel.get(id=1)
    profile = BackupProfileModel.get(id=1)
    tab = DummyTab(profile_provider=lambda: BackupProfileModel.get(id=profile.id))

    profile_signal = FakeSignal()
    repo_signal = FakeSignal()
    tab.bind_profile_attr(profile_signal, 'compression')
    tab.bind_repo_attr(repo_signal, 'name')

    profile_signal.emit('none')
    repo_signal.emit('Renamed Repo')

    assert BackupProfileModel.get(id=profile.id).compression == 'none'
    assert RepoModel.get(id=repo.id).name == 'Renamed Repo'


def test_base_tab_falls_back_to_window_current_profile(qapp, qtbot):
    profile = BackupProfileModel.get(id=1)
    host = QWidget()
    host.current_profile = profile
    qtbot.addWidget(host)

    tab = DummyTab(parent=host)

    assert tab.current_profile().id == profile.id
    assert tab.profile().id == profile.id


def test_base_tab_handles_missing_current_profile(qapp, qtbot):
    host = QWidget()
    qtbot.addWidget(host)
    tab = DummyTab(parent=host)

    assert tab.current_profile() is None
    with pytest.raises(RuntimeError, match="No active backup profile"):
        tab.profile()
