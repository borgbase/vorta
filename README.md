# Vorta - BorgBackup GUI

[Vorta](http://memory-alpha.wikia.com/wiki/Vorta) is a GUI for [BorgBackup](https://borgbackup.readthedocs.io). It's in alpha-status and currently has the following features:

- Select and manage SSH keys
- Initialize new remote Borg repositories
- Create new Borg snapshots (backups) from local folders
- Display existing snapshots and repository details.

Planned features:

- Scheduling for background backups.
- Rule-based scheduling by time, Wifi SSID, etc.
- Repo pruning
- Repo checking
- Securely save repo password in Keychain instead of database.
- Handle encrypted SSH keys
- Check for duplicate source dirs

## Development

