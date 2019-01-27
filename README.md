# Vorta Backup Client <img alt="Logo" src="https://files.qmax.us/vorta/vorta-512px.png" align="right" height="50">

Vorta is a backup client for macOS and Linux desktops. It integrates the mighty [BorgBackup](https://borgbackup.readthedocs.io) with your desktop environment to protect your data from disk failure, ransomware and theft.

![](https://files.qmax.us/vorta-screencast-6.gif)

## Why is this great? 🤩

- **Encrypted, deduplicated and compressed backups** using [Borg](https://borgbackup.readthedocs.io) as backend.
- **No vendor lock-in** – back up to local drives, your own server or [BorgBase](https://www.borgbase.com), a hosting service for Borg backups.
- **Open source** – free to use, modify, improve and audit.
- **Flexible profiles** to group source folders, backup destinations and schedules.
- **One place** to view all point-in-time archives and restore individual files.


## Installation
Vorta should work on all platforms that support Qt and Borg. This includes macOS, Ubuntu, Debian, Fedora, Arch Linux and many others. Windows is currently not supported by Borg, but this may change in the future.

For available packages and instructions, see [INSTALL.md](https://github.com/borgbase/vorta/blob/master/INSTALL.md)


## Learn More
- [Description](https://borgbackup.readthedocs.io/en/stable/internals.html) of Borg's internal workings and security
- [High level guide and template](https://docs.borgbase.com/backup-strategy/steps-with-template/) on setting up a complete backup strategy
- [Detailed tutorial](https://docs.borgbase.com/macos/how-to-backup-your-mac-using-the-vorta-backup-gui/) on setting up Vorta
- Why the name? [Vorta](http://memory-alpha.wikia.com/wiki/Vorta) are a race referenced in Star Trek. After dying they are replaced by their cloned backup.


## Development and Bugs
- Report bugs and submit feature ideas by opening a new [Github issue](https://github.com/borgbase/vorta/issues/new/choose).
- Want to contribute to Vorta? Great! See [CONTRIBUTING.md](https://github.com/borgbase/vorta/blob/master/CONTRIBUTING.md)

## License and Credits
- Thank you to all the people who already contributed to Vorta: [code](https://github.com/borgbase/vorta/graphs/contributors), [translations](https://github.com/borgbase/vorta/issues/159)
- Licensed under GPLv3. See [LICENSE.txt](LICENSE.txt) for details.
- Based on [PyQt](https://riverbankcomputing.com/software/pyqt/intro) and [Qt](https://www.qt.io).
- Icons by [FontAwesome](https://fontawesome.com)
