# Vorta - A Boring GUI for BorgBackup

![](https://files.qmax.us/vorta-screencast-2.gif)

[Vorta](http://memory-alpha.wikia.com/wiki/Vorta) is a GUI for [BorgBackup](https://borgbackup.readthedocs.io). It's in alpha status and currently has the following features:

- [x] Select and manage SSH keys
- [x] Initialize new remote Borg repositories
- [x] Create new Borg snapshots (backups) from local folders
- [x] Mount existing snapshots with FUSE
- [x] Settings stored in sqlite
- [x] Exclude options/patterns.

Missing features:

- [ ] Scheduling for background backups.
- [ ] Rule-based scheduling by time, Wifi SSID, etc.
- [ ] Repo pruning
- [ ] Repo checking
- [ ] Securely save repo password in Keychain instead of database.
- [ ] Handle encrypted SSH keys
- [ ] Check for duplicate source dirs

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

## Why the Name?
[Vorta](http://memory-alpha.wikia.com/wiki/Vorta) are a race referenced in Star Trek. They serve the Dominion and are replaced by their clones if they die. Just like our backups.

## Author
(C) 2018 Manuel Riel for [BorgBase.com](https://www.borgbase.com)

## License and Credits
- Licensed under GPLv3. See LICENSE.txt for details.
- Uses the excellent [BorgBackup](https://www.borgbackup.org)
- Based on PyQt and Qt.
- Icons by [FontAwesome](https://fontawesome.com)
