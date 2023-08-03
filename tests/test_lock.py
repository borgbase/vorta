import pytest
import vorta.application
import vorta.borg.borg_job
from PyQt6 import QtCore


def test_create_perm_error(qapp, borg_json_output, mocker, qtbot):
    main = qapp.main_window
    mocker.patch.object(vorta.application.QMessageBox, 'show')

    stdout, stderr = borg_json_output('create_perm')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    qtbot.mouseClick(main.createStartBtn, QtCore.Qt.MouseButton.LeftButton)

    qtbot.waitUntil(lambda: hasattr(qapp, '_msg'), **pytest._wait_defaults)
    assert qapp._msg.text().startswith("You do not have permission")
    del qapp._msg


def test_create_lock(qapp, borg_json_output, mocker, qtbot):
    main = qapp.main_window
    mocker.patch.object(vorta.application.QMessageBox, 'show')

    # Trigger locked repo
    stdout, stderr = borg_json_output('create_lock')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    qtbot.mouseClick(main.createStartBtn, QtCore.Qt.MouseButton.LeftButton)

    qtbot.waitUntil(lambda: hasattr(qapp, '_msg'), **pytest._wait_defaults)
    assert "The repository at" in qapp._msg.text()

    # Break locked repo
    stdout, stderr = borg_json_output('create_break')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_job, 'Popen', return_value=popen_result)

    qtbot.waitUntil(lambda: main.createStartBtn.isEnabled(), **pytest._wait_defaults)  # Prevent thread collision
    qapp._msg.accept()
    exp_message_text = 'Repository lock broken. Please redo your last action.'
    qtbot.waitUntil(lambda: exp_message_text in main.progressText.text(), **pytest._wait_defaults)
