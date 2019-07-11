# Installing

## Apple macOS
Install via [Homebrew Cask](https://brew.sh/) or download a pre-built app bundle for macOS (10.13+) from [Releases](https://github.com/borgbase/vorta/releases).
```
$ brew cask install vorta
```

## Linux

### Flatpak

<a href='https://flathub.org/apps/details/com.borgbase.Vorta'><img width='240' alt='Download on Flathub' src='https://flathub.org/assets/badges/flathub-badge-en.png'/></a>

Settings can be transferred by copying ~/.local/share/Vorta/settings.db to ~/.var/app/com.borgbase.Vorta/data/Vorta/.

### Distribution Packages
If you added Vorta to a Linux distribution, open an issue or PR and it will be added here.


#### Arch Linux
Use the [AUR package](https://aur.archlinux.org/packages/vorta/) maintained by [@bjo81](https://github.com/bjo81).
```
$ yaourt -S vorta
```

### Desktop Tray Icon
Unless Vorta is started with the `--foreground` option, it will minimize to the system tray without opening a settings window. Be sure your desktop environment supports tray icons by e.g. installing this [Gnome extension](https://extensions.gnome.org/extension/615/appindicator-support/).



## Install from Source
The generic way is to install it as Python package using [pip](https://pip.readthedocs.io/en/stable/installing/). First [install](https://borgbackup.readthedocs.io/en/stable/installation.html) Borg using the package of your distribution or via pip. The latter needs some additional [source packages](https://borgbackup.readthedocs.io/en/stable/installation.html#dependencies). Then install Vorta via pip. Your local Python version must be >= 3.6.
```
$ pip3 install vorta
```

