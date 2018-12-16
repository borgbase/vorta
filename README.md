# Vorta Backup Client <img alt="Logo" src="https://files.qmax.us/vorta/vorta-512px.png" align="right" height="50">

Vorta is a backup client for macOS and Linux desktops. It integrates the mighty [BorgBackup](https://borgbackup.readthedocs.io) with your desktop environment to protect your data from disk failure, ransomware and theft.

![](https://files.qmax.us/vorta-screencast-6.gif)

## Why is this great? 🤩

- **Encrypted, deduplicated and compressed backups** using [Borg](https://borgbackup.readthedocs.io) as backend.
- **No vendor lock-in** – back up to local drives, your own server or [BorgBase](https://www.borgbase.com), a hosting service for Borg backups.
- **Open source** – free to use, modify, improve and audit.
- **Flexible profiles** to group source folders, backup destinations and schedules.
- **One place** to view all point-in-time archives and restore individual files.


## Learn More
- [Description](https://borgbackup.readthedocs.io/en/stable/internals.html) of Borg's internal workings and security
- [High level guide and template](https://docs.borgbase.com/backup-strategy/steps-with-template/) on setting up a complete backup strategy
- [Detailed tutorial](https://docs.borgbase.com/macos/how-to-backup-your-mac-using-the-vorta-backup-gui/) on setting up Vorta

## Installation
Vorta should work on all platforms that support Qt and Borg. This includes macOS, Ubuntu, Debian, Fedora, Arch Linux and many others. Windows is currently not supported by Borg, but this may change in the future.

### Distribution Packages
If available, prefer distribution-specific packages, as they offer better integration.

**Apple macOS**: Install via [Homebrew Cask](https://brew.sh/) or download a pre-built app bundle for macOS (10.13+) from [Releases](https://github.com/borgbase/vorta/releases).
```
$ brew cask install vorta
```
**Arch Linux**: Use the [AUR package](https://aur.archlinux.org/packages/vorta/) maintained by [@bjo81](https://github.com/bjo81).
```
$ yaourt -S vorta
```

### Install from Source
The generic way is to install it as Python package using [PIP](https://pip.readthedocs.io/en/stable/installing/). First [install](https://borgbackup.readthedocs.io/en/stable/installation.html) Borg using the package of your distribution or via PyPI. The latter needs some additional [source packages](https://borgbackup.readthedocs.io/en/stable/installation.html#dependencies). Then install Vorta from PyPI. Your local Python version should be >= 3.6.
```
$ pip3 install vorta
```

## Development and Bug Reports
- Report bugs and submit feature ideas by opening a new [Github issue](https://github.com/borgbase/vorta/issues/new/choose).
- Want to contribute to Vorta? Great! See [CONTRIBUTING.md](CONTRIBUTING.md)

### Why the Name?
[Vorta](http://memory-alpha.wikia.com/wiki/Vorta) are a race referenced in Star Trek. They serve the Dominion and are replaced by their clones if they die. Just like our backups.

## Privacy Policy
- No personal data is ever stored or transmitted by this application.
- During beta-testing, crash reports are sent to [Sentry](https://sentry.io) to quickly find bugs. You can disable bug reports under the **Misc** settings tab. Your repo password will always be scrubbed *before* the test report is transmitted.

## License and Credits
- Ⓒ 2018 [Manuel Riel](https://twitter.com/_m3nu) for [BorgBase.com](https://www.borgbase.com). All rights reserved.
- Licensed under GPLv3. See [LICENSE.txt](LICENSE.txt) for details.
- Based on [PyQt](https://riverbankcomputing.com/software/pyqt/intro) and [Qt](https://www.qt.io).
- Icons by [FontAwesome](https://fontawesome.com)
