"""
Test initialization of new repositories and adding existing ones.
"""

import os
from pathlib import PurePath

import pytest
import vorta.borg
import vorta.utils
import vorta.views.repo_add_dialog
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

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

    add_repo_window.run()

    qtbot.waitUntil(lambda: main.repoTab.repoSelector.count() == 2, **pytest._wait_defaults)

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
    qtbot.mouseClick(main.repoTab.repoRemoveToolbutton, Qt.MouseButton.LeftButton)
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

    # check that repo was added
    qtbot.waitUntil(lambda: tab.repoSelector.count() == 1, **pytest._wait_defaults)
    assert vorta.store.models.RepoModel.select().first().url == str(current_repo_path)
    assert vorta.store.models.RepoModel.select().first().name == TEST_REPO_NAME
