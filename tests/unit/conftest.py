import os
import time
from datetime import datetime as dt

import pytest
from peewee import SqliteDatabase
from test_constants import TEST_SOURCE_DIR, TEST_TEMP_DIR

import vorta
import vorta.application
import vorta.borg.borg_job
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
    qapp.main_window.deleteLater()
    # Skip QCoreApplication.processEvents() - it can trigger D-Bus operations that hang in CI.
    # Use a small sleep instead to allow deleteLater to be processed.
    time.sleep(0.1)
    del qapp.main_window
    qapp.main_window = MainWindow(qapp)


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
    tmp_db = tmpdir_factory.mktemp('Vorta').join('settings.sqlite')
    mock_db = SqliteDatabase(
        str(tmp_db),
        pragmas={
            'journal_mode': 'wal',
        },
    )
    vorta.store.connection.init_db(mock_db)

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

    # Disconnect ALL signal handlers before destroying main_window to avoid "deleted object" errors
    # Using disconnect_all() instead of disconnect() to ensure ALL handlers are removed,
    # not just one (which can leave stale connections from previous tests)
    disconnect_all(qapp.scheduler.schedule_changed)

    # Reload the window to apply the mock data
    # If this test has the `window_load` fixture,
    # it is responsible for calling this instead
    if 'window_load' not in request.fixturenames:
        load_window(qapp)

    yield

    # Teardown: cancel jobs and disconnect ALL signal handlers to prevent state leakage
    qapp.jobs_manager.cancel_all_jobs()

    # Wait for all worker threads to actually exit (not just for current_job to be None).
    # Use simple polling instead of qtbot.waitUntil to avoid Qt event loop hangs in CI.
    # qtbot.waitUntil processes Qt events while waiting, which can trigger D-Bus operations.
    timeout = pytest._wait_defaults.get('timeout', 20000) / 1000  # Convert ms to seconds
    start = time.time()
    while not all_workers_finished(qapp.jobs_manager):
        if time.time() - start > timeout:
            break
        time.sleep(0.1)

    # Skip QCoreApplication.processEvents() - it can trigger D-Bus operations that hang in CI

    # Disconnect signals
    disconnect_all(qapp.backup_finished_event)
    disconnect_all(qapp.scheduler.schedule_changed)

    # Clear the workers dict to prevent accumulation of dead thread references
    qapp.jobs_manager.workers.clear()
    qapp.jobs_manager.jobs.clear()
    mock_db.close()


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
def mock_borg_popen(mocker, borg_json_output):
    """
    Mock Popen for tests that trigger multiple Borg jobs (job chaining).

    When a test triggers job chaining (e.g., prune triggers list refresh),
    each Popen call needs fresh file handles. This fixture uses side_effect
    to create new handles for each call, preventing file handle exhaustion.

    Usage:
        mock_borg_popen(['prune', 'list'])  # Prune job, then list job

    For single-command tests, use borg_json_output directly with return_value.
    """

    def _mock_popen(subcommands, returncodes=None):
        if returncodes is None:
            returncodes = [0] * len(subcommands)

        call_count = [0]  # Use list to allow mutation in closure

        def create_mock(*args, **kwargs):
            idx = call_count[0]
            call_count[0] += 1

            if idx < len(subcommands):
                stdout, stderr = borg_json_output(subcommands[idx])
                returncode = returncodes[idx]
            else:
                # Fallback for unexpected extra calls - use last subcommand
                stdout, stderr = borg_json_output(subcommands[-1])
                returncode = returncodes[-1]

            mock = mocker.MagicMock()
            mock.stdout = stdout
            mock.stderr = stderr
            mock.returncode = returncode
            return mock

        mocker.patch.object(vorta.borg.borg_job, 'Popen', side_effect=create_mock)

    return _mock_popen


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
