
from datetime import timedelta

import psutil
from PyQt6.QtCore import QThread, Qt
from PyQt6.QtWidgets import QTableWidgetItem

from vorta.store.models import ArchiveModel, SettingsModel
from vorta.views.utils import get_colored_icon, SizeItem
from vorta.utils import borg_compat, pretty_bytes, find_best_unit_for_sizes, SHELL_PATTERN_ELEMENT

SIZE_DECIMAL_DIGITS = 1


class PopulateArchiveTableAsync(QThread):
    def __init__(self, profile, mount_points, archiveTable):
        QThread.__init__(self)
        self.profile = profile
        self.mount_points = mount_points
        self.archiveTable = archiveTable

    def run(self):
        # get mount points
        self.mount_points, repo_mount_points = get_mount_points(self.profile.repo.url)
        if repo_mount_points:
            self.repo_mount_point = repo_mount_points[0]

        archives = [s for s in self.profile.repo.archives.select().order_by(ArchiveModel.time.desc())]

        # if no archive's name can be found in self.mount_points, then hide the mount point column
        if not any(a.name in self.mount_points for a in archives):
            self.archiveTable.hideColumn(3)
        else:
            self.archiveTable.showColumn(3)

        sorting = self.archiveTable.isSortingEnabled()
        self.archiveTable.setSortingEnabled(False)
        best_unit = find_best_unit_for_sizes((a.size for a in archives), precision=SIZE_DECIMAL_DIGITS)
        for row, archive in enumerate(archives):
            self.archiveTable.insertRow(row)

            formatted_time = archive.time.strftime('%Y-%m-%d %H:%M')
            self.archiveTable.setItem(row, 0, QTableWidgetItem(formatted_time))

            # format units based on user settings for 'dynamic' or 'fixed' units
            fixed_unit = best_unit if SettingsModel.get(key='enable_fixed_units').value else None
            size = pretty_bytes(archive.size, fixed_unit=fixed_unit, precision=SIZE_DECIMAL_DIGITS)
            self.archiveTable.setItem(row, 1, SizeItem(size))

            if archive.duration is not None:
                formatted_duration = str(timedelta(seconds=round(archive.duration)))
            else:
                formatted_duration = ''

            self.archiveTable.setItem(row, 2, QTableWidgetItem(formatted_duration))

            mount_point = self.mount_points.get(archive.name)
            if mount_point is not None:
                item = QTableWidgetItem(mount_point)
                self.archiveTable.setItem(row, 3, item)

            self.archiveTable.setItem(row, 4, QTableWidgetItem(archive.name))

            if archive.trigger == 'scheduled':
                item = QTableWidgetItem(get_colored_icon('clock-o'), '')
                item.setToolTip(self.tr('Scheduled'))
                self.archiveTable.setItem(row, 5, item)
            elif archive.trigger == 'user':
                item = QTableWidgetItem(get_colored_icon('user'), '')
                item.setToolTip(self.tr('User initiated'))
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
                self.archiveTable.setItem(row, 5, item)

        self.archiveTable.setRowCount(len(archives))
        self.archiveTable.setSortingEnabled(sorting)
        item = self.archiveTable.item(0, 0)
        self.archiveTable.scrollToItem(item)

        self.archiveTable.selectionModel().clearSelection()


def get_mount_points(repo_url):
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
                    if repo_url in cmd:
                        i = cmd.index(repo_url)
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
                        if parameter.startswith(repo_url):
                            # mount from this repo

                            # The borg mount command specifies that the mount_point
                            # parameter comes after the archive name
                            if len(proc.cmdline()) > idx + 1:
                                mount_point = proc.cmdline()[idx + 1]

                                # archive or full mount?
                                if parameter[len(repo_url) :].startswith('::'):
                                    archive_name = parameter[len(repo_url) + 2 :]
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

    return mount_points, repo_mounts
