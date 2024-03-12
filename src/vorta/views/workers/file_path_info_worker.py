
from datetime import datetime as dt, timedelta
import unicodedata
import os
import sys
import re
import fnmatch
import psutil

from PyQt6 import QtCore
from PyQt6.QtCore import QFileInfo, QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (QApplication, QFileDialog, QSystemTrayIcon,
    QListWidgetItem, QTableWidgetItem)


class FilePathInfoAsync(QThread):
    signal = pyqtSignal(str, str, str)

    def __init__(self, path, exclude_patterns_str):
        self.path = path
        QThread.__init__(self)
        self.exiting = False
        self.exclude_patterns = []
        for _line in (exclude_patterns_str or '').splitlines():
            line = _line.strip()
            if line != '':
                self.exclude_patterns.append(line)

    def run(self):
        # logger.info("running thread to get path=%s...", self.path)
        self.size, self.files_count = get_path_datasize(self.path, self.exclude_patterns)
        self.signal.emit(self.path, str(self.size), str(self.files_count))


def normalize_path(path):
    """normalize paths for MacOS (but do nothing on other platforms)"""
    # HFS+ converts paths to a canonical form, so users shouldn't be required to enter an exact match.
    # Windows and Unix filesystems allow different forms, so users always have to enter an exact match.
    return unicodedata.normalize('NFD', path) if sys.platform == 'darwin' else path

def get_path_datasize(path, exclude_patterns):
    file_info = QFileInfo(path)

    if file_info.isDir():
        data_size, files_count = get_directory_size(file_info.absoluteFilePath(), exclude_patterns)
    else:
        data_size = file_info.size()
        files_count = 1

    return data_size, files_count


# prepare patterns as borg does
# see `FnmatchPattern._prepare` at
# https://github.com/borgbackup/borg/blob/master//src/borg/patterns.py
def prepare_pattern(pattern):
    """Prepare and process fnmatch patterns as borg does"""
    if pattern.endswith(os.path.sep):
        # trailing sep indicates that the contents should be excluded
        # but not the directory it self.
        pattern = os.path.normpath(pattern).rstrip(os.path.sep)
        pattern += os.path.sep + '*' + os.path.sep
    else:
        pattern = os.path.normpath(pattern) + os.path.sep + '*'

    pattern = pattern.lstrip(os.path.sep)  # sep at beginning is removed
    return re.compile(fnmatch.translate(pattern))


def match(pattern: re.Pattern, path: str):
    """Check whether a path matches the given pattern."""
    path = path.lstrip(os.path.sep) + os.path.sep
    return pattern.match(path) is not None


def get_directory_size(dir_path, exclude_patterns):
    '''Get number of files only and total size in bytes from a path.
    Based off https://stackoverflow.com/a/17936789'''
    exclude_patterns = [prepare_pattern(p) for p in exclude_patterns]

    data_size_filtered = 0
    seen = set()
    seen_filtered = set()

    for dir_path, subdirectories, file_names in os.walk(dir_path, topdown=True):
        is_excluded = False
        for pattern in exclude_patterns:
            if match(pattern, dir_path):
                is_excluded = True
                break

        if is_excluded:
            subdirectories.clear()  # so that os.walk won't walk them
            continue

        for file_name in file_names:
            file_path = os.path.join(dir_path, file_name)

            # Ignore symbolic links, since borg doesn't follow them
            if os.path.islink(file_path):
                continue

            is_excluded = False
            for pattern in exclude_patterns:
                if match(pattern, file_path):
                    is_excluded = True
                    break

            try:
                stat = os.stat(file_path)
                if stat.st_ino not in seen:  # Visit each file only once
                    # this won't add the size of a hardlinked file
                    seen.add(stat.st_ino)
                    if not is_excluded:
                        data_size_filtered += stat.st_size
                        seen_filtered.add(stat.st_ino)
            except (FileNotFoundError, PermissionError):
                continue

    files_count_filtered = len(seen_filtered)

    return data_size_filtered, files_count_filtered
