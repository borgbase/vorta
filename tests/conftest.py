import os
import socket
import subprocess
import sys
import time
from datetime import datetime as dt
from unittest.mock import Mock

import pytest
from packaging.version import Version
from peewee import SqliteDatabase
from PyQt6.QtCore import QCoreApplication

import vorta
import vorta.application
import vorta.borg.jobs_manager

# Used for conditional setup depending on test context
from tests.unit.test_constants import TEST_SOURCE_DIR, TEST_TEMP_DIR
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
from vorta.utils import borg_compat
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


def pytest_configure(config):
    pytest._wait_defaults = {'timeout': 20000}
    os.environ['LANG'] = 'en'  # Ensure we test an English UI

    # Disable pytest-qt's processEvents() calls on macOS to prevent hangs.
    # See: https://github.com/pytest-dev/pytest-qt/issues/223
    if sys.platform == 'darwin':
        try:
            import pytestqt.plugin

            pytestqt.plugin._process_events = lambda: None
        except (ImportError, AttributeError):
            pass

    # Mock D-Bus system bus to prevent hangs in CI (scheduler.py, network_manager.py)
    try:
        from PyQt6 import QtDBus

        _original_system_bus = QtDBus.QDBusConnection.systemBus

        def _mock_system_bus():
            mock_bus = Mock()
            mock_bus.isConnected.return_value = False
            return mock_bus

        QtDBus.QDBusConnection.systemBus = staticmethod(_mock_system_bus)
    except ImportError:
        pass

    # Mock DNS lookups to prevent timeouts in CI (utils._getfqdn)
    _original_getaddrinfo = socket.getaddrinfo
    socket.getaddrinfo = lambda *args, **kwargs: []

    # Mock WiFi enumeration to prevent hangs on headless CI (utils.get_sorted_wifis)
    import vorta.utils

    _original_get_network_status_monitor = vorta.utils.get_network_status_monitor

    def _mock_get_network_status_monitor():
        mock_monitor = Mock()
        mock_monitor.get_known_wifis.return_value = []
        return mock_monitor

    vorta.utils.get_network_status_monitor = _mock_get_network_status_monitor

    # Add custom markers
    config.addinivalue_line(
        "markers",
        "min_borg_version(): set minimum required borg version for a test",
    )


@pytest.fixture(scope='session')
def qapp(tmpdir_factory):
    # DB is required to init QApplication. New DB used for every test.
    tmp_db = tmpdir_factory.mktemp('Vorta').join('settings.sqlite')
    mock_db = SqliteDatabase(str(tmp_db))
    vorta.store.connection.init_db(mock_db)

    # Needs to be disabled before calling VortaApp()
    if sys.platform == 'darwin':
        cfg = vorta.store.models.SettingsModel.get(key='check_full_disk_access')
        cfg.value = False
        cfg.save()

    # Force use of DB keyring instead of system keyring to avoid keychain prompts during tests
    keyring_setting = vorta.store.models.SettingsModel.get(key='use_system_keyring')
    keyring_setting.value = False
    keyring_setting.save()

    from vorta.application import VortaApp

    qapp = VortaApp([])  # Only init QApplication once to avoid segfaults while testing.

    yield qapp
    mock_db.close()
    qapp.quit()


@pytest.fixture(scope='function', autouse=True)
def borg_version(request):
    """
    Determine the real borg version if this is an integration test.
    Otherwise, inject a dummy version to save time and dependencies.
    """
    is_integration = "tests/integration/" in request.node.nodeid
    if not is_integration:
        return '1.2.4', Version('1.2.4')

    borg_ver = os.getenv('BORG_VERSION')
    if not borg_ver:
        borg_ver = subprocess.run(['borg', '--version'], stdout=subprocess.PIPE).stdout.decode('utf-8')
        borg_ver = borg_ver.split(' ')[1].strip()

    # test window does not automatically set borg version
    borg_compat.set_version(borg_ver, borg_compat.path)

    parsed_borg_version = Version(borg_ver)
    return borg_ver, parsed_borg_version


@pytest.fixture(autouse=True)
def min_borg_version(borg_version, request):
    marker = request.node.get_closest_marker('min_borg_version')
    if marker:
        parsed_borg_version = borg_version[1]
        req_version = marker.args[0]
        if parsed_borg_version < Version(req_version):
            pytest.skip(f'skipped due to borg version requirement for test: {req_version}')


@pytest.fixture(scope='function')
def create_test_repo(tmpdir_factory, borg_version):
    repo_path = tmpdir_factory.mktemp('repo')
    source_files_dir = tmpdir_factory.mktemp('borg_src')

    is_borg_v2 = borg_version[1] >= Version('2.0.0b1')

    if is_borg_v2:
        subprocess.run(['borg', '-r', str(repo_path), 'rcreate', '--encryption=none'], check=True)
    else:
        subprocess.run(['borg', 'init', '--encryption=none', str(repo_path)], check=True)

    def create_archive(timestamp, name):
        if is_borg_v2:
            subprocess.run(
                ['borg', '-r', str(repo_path), 'create', '--timestamp', timestamp, name, str(source_files_dir)],
                cwd=str(repo_path),
                check=True,
            )
        else:
            subprocess.run(
                ['borg', 'create', '--timestamp', timestamp, f'{repo_path}::{name}', str(source_files_dir)],
                cwd=str(repo_path),
                check=True,
            )

    # Setup dummy directory structure and mock files
    file_path = os.path.join(source_files_dir, 'file')
    with open(file_path, 'w') as f:
        f.write('test')

    dir_path = os.path.join(source_files_dir, 'dir')
    os.mkdir(dir_path)

    file_path = os.path.join(dir_path, 'file')
    with open(file_path, 'w') as f:
        f.write('test')

    create_archive('2023-06-14T01:00:00', 'test-archive1')

    symlink_path = os.path.join(dir_path, 'symlink')
    os.symlink(file_path, symlink_path)

    hardlink_path = os.path.join(dir_path, 'hardlink')
    os.link(file_path, hardlink_path)

    fifo_path = os.path.join(dir_path, 'fifo')
    os.mkfifo(fifo_path)

    supports_chrdev = True
    try:
        chrdev_path = os.path.join(dir_path, 'chrdev')
        os.mknod(chrdev_path, mode=0o600 | 0o020000)
    except PermissionError:
        supports_chrdev = False

    create_archive('2023-06-14T02:00:00', 'test-archive2')

    os.rename(dir_path, os.path.join(source_files_dir, 'dir1'))
    create_archive('2023-06-14T03:00:00', 'test-archive3')

    for file in os.listdir(os.path.join(source_files_dir, 'dir1')):
        os.rename(os.path.join(source_files_dir, 'dir1', file), os.path.join(source_files_dir, 'dir1', file + '1'))
    create_archive('2023-06-14T04:00:00', 'test-archive4')

    for file in os.listdir(os.path.join(source_files_dir, 'dir1')):
        os.remove(os.path.join(source_files_dir, 'dir1', file))
    create_archive('2023-06-14T05:00:00', 'test-archive5')

    os.chmod(os.path.join(source_files_dir, 'dir1'), 0o700)
    create_archive('2023-06-14T06:00:00', 'test-archive6')

    return repo_path, source_files_dir, supports_chrdev


@pytest.fixture
def window_load(qapp):
    return lambda: load_window(qapp)


@pytest.fixture(scope='function', autouse=True)
def init_db(request, qapp, qtbot, tmpdir_factory):
    is_integration = "tests/integration/" in request.node.nodeid

    tmp_db = tmpdir_factory.mktemp('Vorta').join('settings.sqlite')
    mock_db = SqliteDatabase(
        str(tmp_db),
        pragmas={
            'journal_mode': 'wal',
        },
    )
    vorta.store.connection.init_db(mock_db)

    # Common Settings
    keyring_setting = SettingsModel.get(key='use_system_keyring')
    keyring_setting.value = False
    keyring_setting.save()

    default_profile = BackupProfileModel(name='Default')
    default_profile.save()

    if is_integration:
        try:
            repo_path, source_dir, _ = request.getfixturevalue('create_test_repo')
        except pytest.FixtureLookupError:
            repo_path, source_dir, _ = '/tmp/fake_repo', '/tmp/fake_src', False
        new_repo = RepoModel(url=repo_path)
    else:
        new_repo = RepoModel(url='i0fi93@i593.repo.borgbase.com:repo')

    new_repo.encryption = 'none'
    new_repo.save()

    default_profile.repo = new_repo.id
    default_profile.dont_run_on_metered_networks = False
    default_profile.validation_on = False
    default_profile.save()

    if is_integration:
        source_dir_model = SourceFileModel(
            dir=source_dir, repo=new_repo, dir_size=12, dir_files_count=3, path_isdir=True
        )
        source_dir_model.save()

        qapp.main_window.deleteLater()
        del qapp.main_window
        qapp.main_window = MainWindow(qapp)
        qapp.scheduler.schedule_changed.disconnect()

    else:
        # Unit test extra data
        test_archive = ArchiveModel(snapshot_id='99999', name='test-archive', time=dt(2000, 1, 1, 0, 0), repo=1)
        test_archive.save()

        test_archive1 = ArchiveModel(snapshot_id='99998', name='test-archive1', time=dt(2000, 1, 1, 0, 0), repo=1)
        test_archive1.save()

        source_dir_model = SourceFileModel(
            dir=TEST_SOURCE_DIR, repo=new_repo, dir_size=100, dir_files_count=18, path_isdir=True
        )
        source_dir_model.save()

        disconnect_all(qapp.scheduler.schedule_changed)

        if 'window_load' not in request.fixturenames:
            load_window(qapp)

    yield

    qapp.jobs_manager.cancel_all_jobs()

    if is_integration:
        qtbot.waitUntil(lambda: all_workers_finished(qapp.jobs_manager), **pytest._wait_defaults)
        QCoreApplication.processEvents()
        disconnect_all(qapp.backup_finished_event)
        disconnect_all(qapp.scheduler.schedule_changed)
    else:
        timeout = pytest._wait_defaults.get('timeout', 20000) / 1000
        start = time.time()
        while not all_workers_finished(qapp.jobs_manager):
            if time.time() - start > timeout:
                break
            time.sleep(0.1)

        disconnect_all(qapp.backup_finished_event)
        disconnect_all(qapp.scheduler.schedule_changed)

    qapp.jobs_manager.workers.clear()
    qapp.jobs_manager.jobs.clear()
    mock_db.close()


@pytest.fixture
def choose_file_dialog(request, tmpdir):
    is_integration = "tests/integration/" in request.node.nodeid

    class MockFileDialog:
        def __init__(self, *args, **kwargs):
            if is_integration:
                self.directory = kwargs.get('directory', None)
                self.subdirectory = kwargs.get('subdirectory', None)

        def open(self, func):
            func()

        def selectedFiles(self):
            if not is_integration:
                return [TEST_TEMP_DIR]

            if hasattr(self, 'subdirectory') and self.subdirectory:
                return [str(tmpdir.join(self.subdirectory))]
            elif hasattr(self, 'directory') and self.directory:
                return [str(self.directory)]
            else:
                return [str(tmpdir)]

    return MockFileDialog


@pytest.fixture
def borg_json_output():
    open_files = []

    def _read_json(subcommand):
        stdout = open(f'tests/unit/borg_json_output/{subcommand}_stdout.json')
        stderr = open(f'tests/unit/borg_json_output/{subcommand}_stderr.json')
        open_files.append(stdout)
        open_files.append(stderr)
        return stdout, stderr

    yield _read_json

    for f in open_files:
        try:
            f.close()
        except Exception:
            pass


@pytest.fixture
def rootdir(request):
    is_integration = "tests/integration/" in request.node.nodeid
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if is_integration:
        return os.path.join(base_dir, 'integration')
    return os.path.join(base_dir, 'unit')


@pytest.fixture()
def archive_env(request, qapp, qtbot):
    is_integration = "tests/integration/" in request.node.nodeid
    main: MainWindow = qapp.main_window
    tab: ArchiveTab = main.archiveTab
    main.tabWidget.setCurrentIndex(3)

    if is_integration:
        tab.refresh_archive_list()
        qtbot.waitUntil(lambda: tab.archiveTable.rowCount() > 0, **pytest._wait_defaults)
    else:
        tab.populate_from_profile()
        qtbot.waitUntil(lambda: tab.archiveTable.rowCount() == 2, **pytest._wait_defaults)

    return main, tab
