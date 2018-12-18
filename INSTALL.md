# Installing


## Install from Source
The generic way is to install it as Python package using [PIP](https://pip.readthedocs.io/en/stable/installing/). First [install](https://borgbackup.readthedocs.io/en/stable/installation.html) Borg using the package of your distribution or via PyPI. The latter needs some additional [source packages](https://borgbackup.readthedocs.io/en/stable/installation.html#dependencies). Then install Vorta from PyPI. Your local Python version should be >= 3.6.
```
$ pip3 install vorta
```

## Distribution Packages
If available, prefer distribution-specific packages, as they offer better integration. (If you added Vorta to a Linux distribution, open an issue or PR and it will be added here.)

### Apple macOS
Install via [Homebrew Cask](https://brew.sh/) or download a pre-built app bundle for macOS (10.13+) from [Releases](https://github.com/borgbase/vorta/releases).
```
$ brew cask install vorta
```
### Arch Linux
Use the [AUR package](https://aur.archlinux.org/packages/vorta/) maintained by [@bjo81](https://github.com/bjo81).
```
$ yaourt -S vorta
```
