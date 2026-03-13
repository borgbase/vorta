from __future__ import annotations

from typing import Any, Callable

from PyQt6.QtWidgets import QApplication

from vorta.store.models import BackupProfileModel, RepoModel

ProfileProvider = Callable[[], BackupProfileModel | None]


class BaseTab:
    """
    Shared functionality for tabs and nested pages that depend on the active profile.

    The class keeps track of Qt signal connections so subclasses only need to declare
    what they listen to instead of duplicating disconnect boilerplate.
    """

    def __init__(self, parent: Any = None, profile_provider: ProfileProvider | None = None) -> None:
        super().__init__(parent)
        self.app = QApplication.instance()
        self._profile_provider = profile_provider or self._default_profile_provider
        self._tracked_connections: list[tuple[Any, Any, Any]] = []
        self.destroyed.connect(self._cleanup_tracked_connections)

    def _default_profile_provider(self) -> BackupProfileModel | None:
        current_profile = getattr(self.window(), 'current_profile', None)
        if current_profile is None:
            return None
        return BackupProfileModel.get(id=current_profile.id)

    def current_profile(self) -> BackupProfileModel | None:
        return self._profile_provider()

    def profile(self) -> BackupProfileModel:
        profile = self.current_profile()
        if profile is None:
            raise RuntimeError("No active backup profile is available for this view.")
        return profile

    def repo(self) -> RepoModel | None:
        return self.profile().repo

    def save_profile_attr(self, attr: str, new_value: Any) -> BackupProfileModel:
        profile = self.profile()
        setattr(profile, attr, new_value)
        profile.save()
        return profile

    def save_repo_attr(self, attr: str, new_value: Any) -> RepoModel | None:
        repo = self.repo()
        if repo is None:
            return None
        setattr(repo, attr, new_value)
        repo.save()
        return repo

    def track_signal(self, signal: Any, slot: Callable[..., None]) -> Any:
        connection = signal.connect(slot)
        self._tracked_connections.append((signal, connection, slot))
        return connection

    def track_palette_change(self, callback: Callable[[], None] | None = None) -> Any:
        return self.track_signal(self.app.paletteChanged, self._without_signal_args(callback or self.set_icons))

    def track_profile_change(self, callback: Callable[[], None] | None = None) -> Any:
        return self.track_signal(self.app.profile_changed_event, callback or self.populate_from_profile)

    def track_backup_finished(self, callback: Callable[[], None] | None = None) -> Any:
        return self.track_signal(self.app.backup_finished_event, callback or self.populate_from_profile)

    @staticmethod
    def _without_signal_args(callback: Callable[[], None]) -> Callable[..., None]:
        def wrapped(*_args, **_kwargs):
            callback()

        return wrapped

    def _cleanup_tracked_connections(self) -> None:
        while self._tracked_connections:
            signal, connection, _slot = self._tracked_connections.pop()
            try:
                signal.disconnect(connection)
            except (TypeError, RuntimeError):
                pass

    def populate_from_profile(self) -> None:
        """Template method for subclasses that render the active profile."""

    def set_icons(self) -> None:
        """Template method for subclasses that respond to palette changes."""
