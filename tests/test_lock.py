from PyQt5 import QtCore
from PyQt5.QtWidgets import QMessageBox
import vorta.borg.borg_thread
import vorta.application


def test_create_perm_error(qapp, borg_json_output, mocker, qtbot):
    main = qapp.main_window
    qtbot.addWidget(main)
    mocker.patch.object(vorta.application.QMessageBox, 'show')

    stdout, stderr = borg_json_output('create_perm')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_thread, 'Popen', return_value=popen_result)

    qtbot.mouseClick(main.createStartBtn, QtCore.Qt.LeftButton)

    qtbot.waitUntil(lambda: hasattr(qapp, '_msg'), timeout=10000)
    assert qapp._msg.text().startswith("You do not have permission")
    del qapp._msg

def test_create_lock(qapp, borg_json_output, mocker, qtbot):
    main = qapp.main_window
    qtbot.addWidget(main)
    mocker.patch.object(vorta.application.QMessageBox, 'show')

    # Trigger locked repo
    stdout, stderr = borg_json_output('create_lock')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_thread, 'Popen', return_value=popen_result)

    qtbot.mouseClick(main.createStartBtn, QtCore.Qt.LeftButton)

    qtbot.waitUntil(lambda: hasattr(qapp, '_msg'), timeout=10000)
    assert "The repository at" in qapp._msg.text()

    # Break locked repo
    stdout, stderr = borg_json_output('create_break')
    popen_result = mocker.MagicMock(stdout=stdout, stderr=stderr, returncode=0)
    mocker.patch.object(vorta.borg.borg_thread, 'Popen', return_value=popen_result)

    qtbot.waitUntil(lambda: main.createStartBtn.isEnabled(), timeout=3000)  # Prevent thread collision
    qapp._msg.accept()
    exp_message_text = 'Repository lock broken. Please redo your last action.'
    qtbot.waitUntil(lambda: main.progressText.text() == exp_message_text, timeout=5000)
