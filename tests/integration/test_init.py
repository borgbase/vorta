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


def test_create_repo(qapp, qtbot, monkeypatch, choose_file_dialog, tmpdir):
    """Test initializing a new repository"""
    main = qapp.main_window
    main.repoTab.new_repo()
    add_repo_window = main.repoTab._window

    # create new folder in tmpdir
    new_repo_path = tmpdir.join('new_repo')
    new_repo_path.mkdir()

    monkeypatch.setattr(
        vorta.views.repo_add_dialog,
        "choose_file_dialog",
        lambda *args, **kwargs: choose_file_dialog(*args, **kwargs, subdirectory=new_repo_path.basename),
    )
    qtbot.mouseClick(add_repo_window.chooseLocalFolderButton, Qt.MouseButton.LeftButton)

    qtbot.keyClicks(add_repo_window.passwordLineEdit, LONG_PASSWORD)
    qtbot.keyClicks(add_repo_window.confirmLineEdit, LONG_PASSWORD)

    add_repo_window.run()

    qtbot.waitUntil(lambda: main.repoTab.repoSelector.count() == 2, **pytest._wait_defaults)

    # Check if repo was created in tmpdir
    assert PurePath(main.repoTab.repoSelector.currentText()).parent == tmpdir
    assert PurePath(main.repoTab.repoSelector.currentText()).name == 'new_repo'

    # check that new_repo_path contains folder data
    assert os.path.exists(new_repo_path.join('data'))
    assert os.path.exists(new_repo_path.join('config'))
    assert os.path.exists(new_repo_path.join('README'))


def test_add_existing_repo(qapp, qtbot, monkeypatch, choose_file_dialog):
    """Test adding an existing repository"""
    main = qapp.main_window
    tab = main.repoTab

    main.tabWidget.setCurrentIndex(0)
    current_repo_path = PurePath(main.repoTab.repoSelector.currentText())

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
    add_repo_window.run()

    # check that repo was added
    qtbot.waitUntil(lambda: tab.repoSelector.count() == 1, **pytest._wait_defaults)
    assert tab.repoSelector.currentText() == str(current_repo_path)
