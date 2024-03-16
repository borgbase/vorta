import psutil
from PyQt6.QtCore import QThread, pyqtSignal

from vorta.utils import SHELL_PATTERN_ELEMENT, borg_compat

SIZE_DECIMAL_DIGITS = 1


class MountPointsWorker(QThread):

    signal = pyqtSignal(dict, list)

    def __init__(self, repo_url):
        QThread.__init__(self)
        self.repo_url = repo_url

    def run(self):
        mount_points = {}
        repo_mounts = []
        for proc in psutil.process_iter():
            try:
                name = proc.name()
                if name == 'borg' or name.startswith('python'):
                    if 'mount' not in proc.cmdline():
                        continue

                    if borg_compat.check('V2'):
                        # command line syntax:
                        # `borg mount -r <repo> <mountpoint> <path> (-a <archive_pattern>)`
                        cmd = proc.cmdline()
                        if self.repo_url in cmd:
                            i = cmd.index(self.repo_url)
                            if len(cmd) > i + 1:
                                mount_point = cmd[i + 1]

                                # Archive mount?
                                ao = '-a' in cmd
                                if ao or '--match-archives' in cmd:
                                    i = cmd.index('-a' if ao else '--match-archives')
                                    if len(cmd) >= i + 1 and not SHELL_PATTERN_ELEMENT.search(cmd[i + 1]):
                                        mount_points[mount_point] = cmd[i + 1]
                                else:
                                    repo_mounts.append(mount_point)
                    else:
                        for idx, parameter in enumerate(proc.cmdline()):
                            if parameter.startswith(self.repo_url):
                                # mount from this repo

                                # The borg mount command specifies that the mount_point
                                # parameter comes after the archive name
                                if len(proc.cmdline()) > idx + 1:
                                    mount_point = proc.cmdline()[idx + 1]

                                    # archive or full mount?
                                    if parameter[len(self.repo_url) :].startswith('::'):
                                        archive_name = parameter[len(self.repo_url) + 2 :]
                                        mount_points[archive_name] = mount_point
                                        break
                                    else:
                                        # repo mount point
                                        repo_mounts.append(mount_point)

            except (psutil.ZombieProcess, psutil.AccessDenied, psutil.NoSuchProcess):
                # Getting process details may fail (e.g. zombie process on macOS)
                # or because the process is owned by another user.
                # Also see https://github.com/giampaolo/psutil/issues/783
                continue

        self.signal.emit(mount_points, repo_mounts)
