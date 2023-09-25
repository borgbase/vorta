# Vorta Backup Client <img alt="Logo" src="https://files.qmax.us/vorta/vorta-512px.png" align="right" height="50">

[![GitHub all releases](https://img.shields.io/github/downloads/borgbase/vorta/total?label=downloads&logo=github&color=green)](https://github.com/borgbase/vorta/releases)
[![Flathub](https://img.shields.io/flathub/downloads/com.borgbase.Vorta?logo=flathub&logoColor=white&color=green)](https://flathub.org/apps/details/com.borgbase.Vorta)
[![Github License](https://img.shields.io/github/license/borgbase/vorta?color=bd0000)](https://github.com/borgbase/vorta/blob/master/LICENSE.txt)
[![pypi](https://img.shields.io/pypi/v/vorta.svg?logo=pypi&logoColor=white&color=0073b7)](https://pypi.org/project/vorta/)
[![homebrew cask](https://img.shields.io/homebrew/cask/v/vorta?logo=homebrew&color=fbb040)](https://formulae.brew.sh/cask/vorta)
[![Flathub](https://img.shields.io/flathub/v/com.borgbase.Vorta?color=4a86cf&logo=flathub&logoColor=white)](https://flathub.org/apps/details/com.borgbase.Vorta)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://pre-commit.com)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
<br>
<br>

Vorta is a backup client for macOS and Linux desktops. It integrates the mighty [BorgBackup](https://borgbackup.readthedocs.io) with your desktop environment to protect your data from disk failure, ransomware and theft.

![](https://files.qmax.us/vorta/screencast-8-small.gif)

## Why is this great? 🤩

- **Encrypted, deduplicated and compressed backups** using [Borg](https://borgbackup.readthedocs.io) as backend.
- **No vendor lock-in** – back up to local drives, your own server or [BorgBase](https://www.borgbase.com), a hosting service for Borg backups.
- **Open source** – free to use, modify, improve and audit.
- **Flexible profiles** to group source folders, backup destinations and schedules.
- **One place** to view all point-in-time archives and restore individual files.

Learn more on [Vorta's website](https://vorta.borgbase.com).

## Installation
Vorta should work on all platforms that support Qt and Borg. This includes macOS, Ubuntu, Debian, Fedora, Arch Linux and many others. Windows is currently not supported by Borg, but this may change in the future.

See our website for [download links and install instructions](https://vorta.borgbase.com/install).

## Connect and Contribute
- To discuss everything around using, improving, packaging and translating Vorta, join the [discussion on Github](https://github.com/borgbase/vorta/discussions).
- Report bugs by opening a new [Github issue](https://github.com/borgbase/vorta/issues/new/choose).
- Want to contribute to Vorta? Great! See our [contributor guide](https://vorta.borgbase.com/contributing/) on how to help out with coding, translation and packaging.
- We currently have students from the Google Summer Of Code 2023 Program contributing to this project.

## License and Credits
- See [CONTRIBUTORS.md](CONTRIBUTORS.md) to see who programmed and translated Vorta.
- Licensed under [GPLv3](LICENSE.txt). © 2018-2023 Manuel Riel and Vorta contributors
- Based on [PyQt](https://riverbankcomputing.com/software/pyqt/intro) and [Qt](https://www.qt.io).
- Icons by [Fork Awesome](https://forkaweso.me/) (licensed under [SIL Open Font License](https://scripts.sil.org/OFL), Version 1.1) and Material Design icons by Google (licensed under [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0.txt)). See the `src/vorta/assets/icons` folder for a copy of applicable licenses.
