import os
import sys
import time
from datetime import datetime as dt

import pytest
from peewee import SqliteDatabase
from test_constants import TEST_SOURCE_DIR, TEST_TEMP_DIR

import vorta
import vorta.application
import vorta.borg.jobs_manager
from vorta.store.models import (
    ArchiveModel,
    BackupProfileModel,
    EventLogModel,
    RepoModel,
    RepoPassword,
    SchemaVersion,
    SettingsModel,
    SourceFileModel,
    WifiSettingModel,
)
from vorta.views.main_window import ArchiveTab, MainWindow


# Debug timing helper
def debug_time(label, start_time=None):
    """Print timing debug info. If start_time provided, prints elapsed time."""
    now = time.time()
    if start_time is not None:
        elapsed = now - start_time
        print(f"\n[DEBUG TIMING] {label}: {elapsed:.3f}s", file=sys.stderr, flush=True)
    else:
        print(f"\n[DEBUG TIMING] {label} - starting", file=sys.stderr, flush=True)
    return now


def disconnect_all(signal):
    """
    Disconnect ALL handlers from a Qt signal.
    Unlike signal.disconnect() without arguments which only disconnects ONE handler,
    this function disconnects all connected handlers by calling disconnect in a loop
    until TypeError is raised (indicating no more handlers are connected).
    """
    while True:
        try:
            signal.disconnect()
        except TypeError:
            # No more handlers connected
            break


def all_workers_finished(jobs_manager):
    """
    Check if all worker threads have actually exited.
    This is more thorough than is_worker_running() which only checks current_job,
    because threads may still be alive briefly after current_job is set to None.
    """
    for worker in jobs_manager.workers.values():
        if worker.is_alive():
            return False
    return True


models = [
    RepoModel,
    RepoPassword,
    BackupProfileModel,
    SourceFileModel,
    SettingsModel,
    ArchiveModel,
    WifiSettingModel,
    EventLogModel,
    SchemaVersion,
]


def load_window(qapp: vorta.application.VortaApp):
    """
    Reload the main window of the given application.
    Used to repopulate fields after loading mock data.
    """
    t0 = debug_time("load_window: deleteLater")
    qapp.main_window.deleteLater()
    # Skip QCoreApplication.processEvents() - it can trigger D-Bus operations that hang in CI.
    # Use a small sleep instead to allow deleteLater to be processed.
    time.sleep(0.1)
    t1 = debug_time("load_window: after sleep", t0)
    del qapp.main_window
    t2 = debug_time("load_window: creating MainWindow", t1)
    qapp.main_window = MainWindow(qapp)
    debug_time("load_window: MainWindow created", t2)


@pytest.fixture
def window_load(qapp):
    """
    A function to call to load fixture data into the app window.

    This is normally done by init_db, but if this fixture is used,
    the window load will be skipped to allow the test to load
    further data before then calling the returned function
    """
    return lambda: load_window(qapp)


@pytest.fixture(scope='function', autouse=True)
def init_db(qapp, qtbot, tmpdir_factory, request):
    t_setup_start = debug_time(f"init_db SETUP: {request.node.name}")

    tmp_db = tmpdir_factory.mktemp('Vorta').join('settings.sqlite')
    mock_db = SqliteDatabase(
        str(tmp_db),
        pragmas={
            'journal_mode': 'wal',
        },
    )
    t1 = debug_time("init_db: calling vorta.store.connection.init_db", t_setup_start)
    vorta.store.connection.init_db(mock_db)
    t2 = debug_time("init_db: store.connection.init_db done", t1)

    # Force use of DB keyring instead of system keyring to avoid keychain prompts during tests
    keyring_setting = SettingsModel.get(key='use_system_keyring')
    keyring_setting.value = False
    keyring_setting.save()

    default_profile = BackupProfileModel(name='Default')
    default_profile.save()

    new_repo = RepoModel(url='i0fi93@i593.repo.borgbase.com:repo')
    new_repo.encryption = 'none'
    new_repo.save()

    default_profile.repo = new_repo.id
    default_profile.dont_run_on_metered_networks = False
    default_profile.validation_on = False
    default_profile.save()

    test_archive = ArchiveModel(snapshot_id='99999', name='test-archive', time=dt(2000, 1, 1, 0, 0), repo=1)
    test_archive.save()

    test_archive1 = ArchiveModel(snapshot_id='99998', name='test-archive1', time=dt(2000, 1, 1, 0, 0), repo=1)
    test_archive1.save()

    source_dir = SourceFileModel(dir=TEST_SOURCE_DIR, repo=new_repo, dir_size=100, dir_files_count=18, path_isdir=True)
    source_dir.save()
    debug_time("init_db: models created", t2)

    # Disconnect ALL signal handlers before destroying main_window to avoid "deleted object" errors
    # Using disconnect_all() instead of disconnect() to ensure ALL handlers are removed,
    # not just one (which can leave stale connections from previous tests)
    disconnect_all(qapp.scheduler.schedule_changed)

    # Reload the window to apply the mock data
    # If this test has the `window_load` fixture,
    # it is responsible for calling this instead
    if 'window_load' not in request.fixturenames:
        load_window(qapp)
    debug_time("init_db SETUP complete", t_setup_start)

    yield

    # Teardown: cancel jobs and disconnect ALL signal handlers to prevent state leakage
    t_teardown_start = debug_time(f"init_db TEARDOWN: {request.node.name}")

    # Log worker state before cancel
    workers_info = {
        k: {'alive': w.is_alive(), 'current_job': w.current_job} for k, w in qapp.jobs_manager.workers.items()
    }
    print(f"\n[DEBUG] Workers before cancel: {workers_info}", file=sys.stderr, flush=True)

    qapp.jobs_manager.cancel_all_jobs()
    t1 = debug_time("init_db: cancel_all_jobs done", t_teardown_start)

    # Wait for all worker threads to actually exit (not just for current_job to be None).
    # Use simple polling instead of qtbot.waitUntil to avoid Qt event loop hangs in CI.
    # qtbot.waitUntil processes Qt events while waiting, which can trigger D-Bus operations.
    timeout = pytest._wait_defaults.get('timeout', 20000) / 1000  # Convert ms to seconds
    start = time.time()
    wait_iterations = 0
    while not all_workers_finished(qapp.jobs_manager):
        wait_iterations += 1
        if wait_iterations % 50 == 0:  # Log every 5 seconds
            workers_alive = {k: w.is_alive() for k, w in qapp.jobs_manager.workers.items()}
            print(
                f"\n[DEBUG] Still waiting for workers after {time.time() - start:.1f}s: {workers_alive}",
                file=sys.stderr,
                flush=True,
            )
        if time.time() - start > timeout:
            print(f"\n[DEBUG] Worker wait TIMED OUT after {timeout}s", file=sys.stderr, flush=True)
            break
        time.sleep(0.1)
    t2 = debug_time(f"init_db: worker wait done (iterations={wait_iterations})", t1)

    # Skip QCoreApplication.processEvents() - it can trigger D-Bus operations that hang in CI

    # Disconnect signals
    disconnect_all(qapp.backup_finished_event)
    disconnect_all(qapp.scheduler.schedule_changed)

    # Clear the workers dict to prevent accumulation of dead thread references
    qapp.jobs_manager.workers.clear()
    qapp.jobs_manager.jobs.clear()
    mock_db.close()
    debug_time("init_db TEARDOWN complete", t_teardown_start)


@pytest.fixture
def choose_file_dialog(*args):
    class MockFileDialog:
        def __init__(self, *args, **kwargs):
            pass

        def open(self, func):
            func()

        def selectedFiles(self):
            return [TEST_TEMP_DIR]

    return MockFileDialog


@pytest.fixture
def borg_json_output():
    """
    Returns a function to read borg JSON output files.
    Opens real file handles (required for os.set_blocking and select.select),
    but tracks them for cleanup when the fixture is torn down.
    """
    open_files = []

    def _read_json(subcommand):
        stdout = open(f'tests/unit/borg_json_output/{subcommand}_stdout.json')
        stderr = open(f'tests/unit/borg_json_output/{subcommand}_stderr.json')
        open_files.append(stdout)
        open_files.append(stderr)
        return stdout, stderr

    yield _read_json

    # Clean up all opened files when the fixture is torn down
    for f in open_files:
        try:
            f.close()
        except Exception:
            pass


@pytest.fixture
def rootdir():
    return os.path.dirname(os.path.abspath(__file__))


@pytest.fixture()
def archive_env(qapp, qtbot):
    """
    Common setup for unit tests involving the archive tab.
    """
    main: MainWindow = qapp.main_window
    tab: ArchiveTab = main.archiveTab
    main.tabWidget.setCurrentIndex(3)
    tab.populate_from_profile()
    qtbot.waitUntil(lambda: tab.archiveTable.rowCount() == 2, **pytest._wait_defaults)
    return main, tab
