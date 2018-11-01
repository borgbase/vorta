# Vorta - A Boring GUI for BorgBackup

![](https://files.qmax.us/vorta-screencast-2.gif)

Vorta is a macOS/Linux GUI for [BorgBackup](https://borgbackup.readthedocs.io). It's currently in alpha status. 

## Main features

- Encrypted, deduplicated and compressed backups to remote repositories
- Works with any remote SSH account that has `borg` installed. Or try [BorgBase](https://www.borgbase.com) for advanced features like append-only repositories and monitoring.
- Add SSH keys and initialize repos directly from the GUI
- Repo keys are securely stored in macOS Keychain, Secret Service or KWallet
- Mount existing snapshots via FUSE
- Flexible scheduling for automatic background backups.
- View a list of snapshots and action logs
- Exclude options/patterns.

Missing features: (PRs welcome)

- [ ] Repo pruning
- [ ] Repo checking
- [ ] Full test coverage
- [ ] Packaging for Linux

## Installation and Download
### macOS
The app package under [Releases](https://github.com/borgbase/vorta/releases) should include everything. Just download, unzip and run.

### Linux
No package yet. First install Borg's own [dependencies](https://borgbackup.readthedocs.io/en/stable/installation.html#dependencies). Then install via
```
$ pip install vorta
```

After installation run with the `vorta` command.
```
$ vorta
```

## Development
Install in development mode:
```
$ pip install -e .
```

Then run via
```
$ vorta
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
Tests are in the folder `/tests`. Testing happens at the level of UI components. Calls to `borg` are mocked and can be replaced with some example json-output. To run tests:
```
$ python setup.py test
```

## Privacy Policy
- No personal data is ever stored or transmitted by this application.
- During beta, crash reports are sent to [Sentry](https://sentry.io) to quickly find bugs.

## Why the Name?
[Vorta](http://memory-alpha.wikia.com/wiki/Vorta) are a race referenced in Star Trek. They serve the Dominion and are replaced by their clones if they die. Just like our backups.

## Author
(C) 2018 Manuel Riel for [BorgBase.com](https://www.borgbase.com)

## License and Credits
- Licensed under GPLv3. See LICENSE.txt for details.
- Uses the excellent [BorgBackup](https://www.borgbackup.org)
- Based on PyQt and Qt.
- Icons by [FontAwesome](https://fontawesome.com)
