import os
import sys
import time

import pytest
from peewee import SqliteDatabase

import vorta
import vorta.application
import vorta.borg.jobs_manager


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


def pytest_configure(config):
    sys._called_from_test = True
    pytest._wait_defaults = {'timeout': 20000}
    os.environ['LANG'] = 'en'  # Ensure we test an English UI


@pytest.fixture(scope='session')
def qapp(tmpdir_factory):
    t_start = debug_time("qapp fixture: starting")

    # DB is required to init QApplication. New DB used for every test.
    tmp_db = tmpdir_factory.mktemp('Vorta').join('settings.sqlite')
    mock_db = SqliteDatabase(str(tmp_db))
    t1 = debug_time("qapp: calling init_db", t_start)
    vorta.store.connection.init_db(mock_db)
    t2 = debug_time("qapp: init_db done", t1)

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

    t3 = debug_time("qapp: creating VortaApp", t2)
    qapp = VortaApp([])  # Only init QApplication once to avoid segfaults while testing.
    debug_time("qapp: VortaApp created", t3)

    # Log initial workers state with more detail
    for k, w in qapp.jobs_manager.workers.items():
        job = w.current_job
        job_info = f"{job.__class__.__name__}" if job else "None"
        process_info = "N/A"
        if job and hasattr(job, 'process') and job.process:
            proc = job.process
            process_info = f"pid={proc.pid}, poll={proc.poll()}"
        print(
            f"\n[DEBUG] Worker {k}: alive={w.is_alive()}, job={job_info}, process={process_info}",
            file=sys.stderr,
            flush=True,
        )

    debug_time("qapp fixture: setup complete", t_start)

    yield qapp
    mock_db.close()
    qapp.quit()
