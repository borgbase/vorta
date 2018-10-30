# Vorta - A Boring GUI for BorgBackup

![](https://files.qmax.us/vorta-screencast-2.gif)

[Vorta](http://memory-alpha.wikia.com/wiki/Vorta) is a GUI for [BorgBackup](https://borgbackup.readthedocs.io). It's in alpha status and currently has the following features:

- [x] Select and create SSH keys without using the Terminal
- [x] Securely save repo password in Keychain.
- [x] Initialize new remote Borg repositories
- [x] Create new Borg snapshots (backups) from local folders
- [x] Mount existing snapshots with FUSE
- [x] Settings stored in sqlite
- [x] Exclude options/patterns.
- [x] Rule-based scheduling by time, Wifi SSID, etc.
- [x] Scheduling for background backups.
- [x] Tests (partly)

Missing features:

- [ ] Repo pruning
- [ ] Repo checking

## Download
The app package under [Releases](https://github.com/borgbase/vorta/releases) should include everything. Just download, unzip and run.

## Development
Conda is used for dependency management. Create a new virtual env using:
```
$ conda env create environment.yml
```

Qt Creator is used to edit views. Install using Homebrew and then open the .ui files in `vorta/UI`:
```
$ brew cask install qt-creator
$ brew install qt
```

To build a binary package:
```
$ pyinstaller --clean --noconfirm vorta.spec 
```

### Testing (work in progress)
Tests are in the folder `/tests`. Run them with `PYTHONPATH=src pytest`. Testing happens at the level of UI components. Calls to `borg` are mocked and can be replaced with some example json-output.


## Why the Name?
[Vorta](http://memory-alpha.wikia.com/wiki/Vorta) are a race referenced in Star Trek. They serve the Dominion and are replaced by their clones if they die. Just like our backups.

## Author
(C) 2018 Manuel Riel for [BorgBase.com](https://www.borgbase.com)

## License and Credits
- Licensed under GPLv3. See LICENSE.txt for details.
- Uses the excellent [BorgBackup](https://www.borgbackup.org)
- Based on PyQt and Qt.
- Icons by [FontAwesome](https://fontawesome.com)
