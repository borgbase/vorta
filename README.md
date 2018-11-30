# Vorta - A Boring Open Source GUI for BorgBackup
[![Build Status](https://travis-ci.org/borgbase/vorta.svg?branch=master)](https://travis-ci.org/borgbase/vorta)

![](https://files.qmax.us/vorta-screencast-5.gif)

Vorta is an open source macOS/Linux GUI for [BorgBackup](https://borgbackup.readthedocs.io). It's currently in beta status. 

## Main features

- Encrypted, deduplicated and compressed backups using `borg` as battle-tested backend.
- Works with any local or remote Borg repo. Try [BorgBase](https://www.borgbase.com) for advanced features like append-only repositories and monitoring.
- Repo keys are securely stored in macOS Keychain, SecretService or KWallet. Create SSH keys directly from the GUI.
- Manage multiple backup profiles with different source folders, destinations and settings.
- Flexible scheduling for automatic background backups. Only allow on certain Wifis.
- Restore files from mounts or using the built-in backup browser.

## Installation and Download
Vorta should work on all platforms that support Qt and Borg. Currently Borg doesn't support Windows, but this may change in the future. Setting allowed Wifi networks is currently not supported on Linux, but everything else should work.

### macOS
Download the pre-built macOS binary from [Releases](https://github.com/borgbase/vorta/releases). Just download, unzip and run. If you want detailed steps, there is also a [tutorial](https://docs.borgbase.com/macos/how-to-backup-your-mac-using-the-vorta-backup-gui/).

### Linux
First install Borg and its [dependencies](https://borgbackup.readthedocs.io/en/stable/installation.html#dependencies). Then install Vorta from Pypi:
```
$ pip install vorta
```

After installation run with the `vorta` command.
```
$ vorta
```

## Debugging and Bugs
Please report any errors you may encounter by [opening an issue](https://github.com/borgbase/vorta/issues) on Github. Please include steps to reproduce and all logging output. Logs can be found in these folders:

- Linux: `$HOME/.cache/Vorta/log`
- macOS: `$HOME/Library/Logs/Vorta`

## Development

Install in development/editable mode while in the repo:
```
$ pip install -e .
```

Then run as Python script:
```
$ vorta
```

Install developer packages we use (pytest, tox, pyinstaller):
```
pip install -r requirements-dev.txt
```

Qt Creator is used to edit views. Install from [their site](https://www.qt.io/download) or using Homebrew and then open the .ui files in `vorta/UI`:
```
$ brew cask install qt-creator
$ brew install qt
```

To build a macOS app package:
- add `Sparkle.framework` from [here](https://github.com/sparkle-project/Sparkle) and `borg` from [here](https://github.com/borgbackup/borg/releases) in `bin/macosx64`
- then uncomment or change the Apple signing profile to be used in `Makefile`
- finally run to `$ make Vorta.app` to build the app into the `dist` folder.

### Testing (work in progress)

Tests are in the folder `/tests`. Testing happens at the level of UI components. Calls to `borg` are mocked and can be replaced with some example json-output. To run tests:
```
$ pytest
```

## Why the Name?
[Vorta](http://memory-alpha.wikia.com/wiki/Vorta) are a race referenced in Star Trek. They serve the Dominion and are replaced by their clones if they die. Just like our backups.

## Privacy Policy
- No personal data is ever stored or transmitted by this application.
- During beta, crash reports are sent to [Sentry](https://sentry.io) to quickly find bugs. You can disable this by setting the env variable `NO_SENTRY=1`. Your repo password will be scrubbed *before* the test report is transmitted.

## Author
(C) 2018 Manuel Riel for [BorgBase.com](https://www.borgbase.com)

## License and Credits
- Licensed under GPLv3. See LICENSE.txt for details.
- Uses the excellent [BorgBackup](https://www.borgbackup.org)
- Based on [PyQt](https://riverbankcomputing.com/software/pyqt/intro) and [Qt](https://www.qt.io).
- Icons by [FontAwesome](https://fontawesome.com)
