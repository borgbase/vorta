"""
Test initialization of new repositories and adding existing ones.
"""

import os
from pathlib import PurePath

import pytest
from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtWidgets import QMessageBox

import vorta.borg
import vorta.utils
import vorta.views.repo_add_dialog
from tests.integration.conftest import all_workers_finished

LONG_PASSWORD = 'long-password-long'
TEST_REPO_NAME = 'TEST - REPONAME'


def test_create_repo(qapp, qtbot, monkeypatch, choose_file_dialog, tmpdir):
    """Test initializing a new repository"""
    main = qapp.main_window
    main.repoTab.new_repo()
    add_repo_window = main.repoTab._window
    main.show()

    # create new folder in tmpdir
    new_repo_path = tmpdir.join('new_repo')
    new_repo_path.mkdir()

    monkeypatch.setattr(
        vorta.views.repo_add_dialog,
        "choose_file_dialog",
        lambda *args, **kwargs: choose_file_dialog(*args, **kwargs, subdirectory=new_repo_path.basename),
    )
    qtbot.mouseClick(add_repo_window.chooseLocalFolderButton, Qt.MouseButton.LeftButton)

    # clear auto input of repo name from url
    add_repo_window.repoName.selectAll()
    add_repo_window.repoName.del_()
    qtbot.keyClicks(add_repo_window.repoName, TEST_REPO_NAME)

    qtbot.keyClicks(add_repo_window.passwordInput.passwordLineEdit, LONG_PASSWORD)
    qtbot.keyClicks(add_repo_window.passwordInput.confirmLineEdit, LONG_PASSWORD)

    initial_count = main.repoTab.repoSelector.count()

    # Mock the key backup prompt to avoid blocking QMessageBox.exec() in headless CI
    monkeypatch.setattr(
        add_repo_window,
        'prompt_key_backup',
        lambda result: (add_repo_window.added_repo.emit(result), add_repo_window.accept()),
    )

    add_repo_window.run()

    # Wait for all worker threads to fully exit (more thorough than is_worker_running)
    qtbot.waitUntil(lambda: all_workers_finished(qapp.jobs_manager), **pytest._wait_defaults)

    # Process pending Qt events to ensure signals are delivered and UI is updated
    QCoreApplication.processEvents()

    # Wait for the new repo to appear in the selector
    qtbot.waitUntil(lambda: main.repoTab.repoSelector.count() == initial_count + 1, **pytest._wait_defaults)

    # Check if repo was created in tmpdir
    repo_url = (
        vorta.store.models.RepoModel.select().where(vorta.store.models.RepoModel.name == TEST_REPO_NAME).get().url
    )
    assert PurePath(repo_url).parent == tmpdir
    assert PurePath(repo_url).name == 'new_repo'

    # check that new_repo_path contains folder data
    assert os.path.exists(new_repo_path.join('data'))
    assert os.path.exists(new_repo_path.join('config'))
    assert os.path.exists(new_repo_path.join('README'))


def test_add_existing_repo(qapp, qtbot, monkeypatch, choose_file_dialog):
    """Test adding an existing repository"""
    main = qapp.main_window
    tab = main.repoTab

    main.tabWidget.setCurrentIndex(0)
    current_repo_path = vorta.store.models.RepoModel.select().first().url

    monkeypatch.setattr(QMessageBox, "show", lambda *args: True)

    # Assuming unlink action is the first in submenu
    tab.menuRepoUtil.actions()[0].trigger()

    qtbot.waitUntil(
        lambda: tab.repoSelector.count() == 1 and tab.repoSelector.currentText() == "No repository selected",
        **pytest._wait_defaults,
    )

    # add existing repo again
    main.repoTab.add_existing_repo()
    add_repo_window = main.repoTab._window

    monkeypatch.setattr(
        vorta.views.repo_add_dialog,
        "choose_file_dialog",
        lambda *args, **kwargs: choose_file_dialog(*args, **kwargs, directory=current_repo_path),
    )
    qtbot.mouseClick(add_repo_window.chooseLocalFolderButton, Qt.MouseButton.LeftButton)

    # clear auto input of repo name from url
    add_repo_window.repoName.selectAll()
    add_repo_window.repoName.del_()
    qtbot.keyClicks(add_repo_window.repoName, TEST_REPO_NAME)

    add_repo_window.run()

    # Wait for all worker threads to fully exit (more thorough than is_worker_running)
    qtbot.waitUntil(lambda: all_workers_finished(qapp.jobs_manager), **pytest._wait_defaults)

    # Process pending Qt events to ensure signals are delivered and UI is updated
    QCoreApplication.processEvents()

    # Wait for the repo to appear in the selector
    # After unlink, count is 1 (only placeholder). After adding repo, count should be 2.
    qtbot.waitUntil(lambda: tab.repoSelector.count() == 2, **pytest._wait_defaults)

    # check that repo was added correctly
    assert vorta.store.models.RepoModel.select().first().url == str(current_repo_path)
    assert vorta.store.models.RepoModel.select().first().name == TEST_REPO_NAME
