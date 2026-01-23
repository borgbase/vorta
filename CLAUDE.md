# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Vorta is a desktop backup client for macOS and Linux that provides a GUI for BorgBackup. It's built with PyQt6 and uses Peewee ORM with SQLite for data persistence.

## Common Commands

This project uses `uv` for Python environment and dependency management. All Python commands should be run via `uv run`.

### Testing
```bash
# Run all tests (uses nox to test against multiple Borg versions)
make test

# Run only unit tests
make test-unit

# Run only integration tests
make test-integration

# Run tests with a specific Borg version
BORG_VERSION=1.2.4 uv run nox -- tests/unit/test_archives.py

# Run a single test file
uv run nox -- tests/unit/test_archives.py

# Run a single test
uv run nox -- tests/unit/test_archives.py::test_archive_add
```

### Linting
```bash
make lint  # Runs pre-commit hooks (ruff linter + formatter)
```

### Building (macOS)
```bash
make dist/Vorta.app  # Build macOS app locally (without Borg)
make dist/Vorta.dmg  # Create notarized macOS DMG
```

### Development Install
```bash
uv sync  # Install dependencies and project in editable mode
```

## Architecture

### Core Components

- **`src/vorta/application.py`**: `VortaApp` - Main application class extending `QtSingleApplication`. Manages the lifecycle, coordinates between components via Qt signals (backup_started_event, backup_finished_event, etc.), and ensures single-instance operation.

- **`src/vorta/borg/`**: Borg command execution layer
  - `borg_job.py`: `BorgJob` base class for running Borg CLI commands in threads. Handles password retrieval from keyring, environment setup, and JSON log parsing.
  - Individual job classes (`create.py`, `prune.py`, `extract.py`, etc.) subclass `BorgJob` with specific `prepare()` and `process_result()` implementations.
  - `jobs_manager.py`: Manages job queues per repository (only one job per repo at a time).

- **`src/vorta/store/`**: Data persistence
  - `models.py`: Peewee models - `BackupProfileModel`, `RepoModel`, `ArchiveModel`, `SourceFileModel`, `ExclusionModel`, `SettingsModel`, etc. All models use a proxied `DB` connection.
  - `migrations.py`: Schema migrations applied on startup.
  - `connection.py`: Database initialization and cleanup.

- **`src/vorta/views/`**: PyQt6 UI components
  - `main_window.py`: Main application window with tabs (Repo, Source, Archive, Schedule, Misc, About).
  - Tab classes (`repo_tab.py`, `source_tab.py`, `archive_tab.py`, etc.) manage their respective UI sections.
  - UI layouts are defined in `.ui` files under `src/vorta/assets/UI/`.

### Platform-Specific Code

- **`src/vorta/keyring/`**: Platform-specific password storage (macOS Keychain, KWallet, SecretStorage, or fallback DB storage)
- **`src/vorta/network_status/`**: Network monitoring (macOS CoreWLAN, Linux NetworkManager)

### Event Flow

1. User initiates backup via UI → `VortaApp.create_backup_action()`
2. `BorgCreateJob.prepare()` validates and builds command
3. Job added to `JobsManager` queue
4. Job runs in thread, emits progress via `backup_progress_event`
5. On completion, `backup_finished_event` triggers UI updates and archive refresh

## Code Style

- Line length: 120 characters
- Formatting: ruff (previously black)
- Linting: ruff with E, F, I, W, YTT rules
- Quote style: preserved (single quotes common)

## Testing Notes

- Tests use pytest with pytest-qt for GUI testing
- Session-scoped `qapp` fixture provides a shared `VortaApp` instance
- Mock database created per test session in temp directory
- Tests are separated into `unit/` and `integration/` directories
- Nox parametrizes tests across Borg versions: 1.1.18, 1.2.2, 1.2.4, 2.0.0b6
