# Contributing
[![Build Status](https://travis-ci.org/borgbase/vorta.svg?branch=master)](https://travis-ci.org/borgbase/vorta)

First off, thanks for taking the time to contribute!

All contributions that improve Vorta for everyone are welcome. Before coding a new feature it's usually best to discuss it with other users under [Issues](https://github.com/borgbase/vorta/issues). Once everything is clear, follow the instructions below to 

## Local Development Setup

Clone the latest version of this repo
```
$ git clone https://github.com/borgbase/vorta/
```

Install in development/editable mode while in the repo root:
```
$ pip install -e .
```

Install additional developer packages (pytest, tox, pyinstaller):
```
pip install -r requirements.d/dev.txt
```

Then run as Python script. Any changes from your source folder should be reflected.
```
$ vorta
```

## Working on the GUI
Qt Creator is used to edit views. Install from [their site](https://www.qt.io/download) or using Homebrew and then open the .ui files in `vorta/UI` with Qt Creator:
```
$ brew cask install qt-creator
$ brew install qt
```

For UI icons, we use Fontawesome. You can browse available icons [here](https://fontawesome.com/icons) and download them as SVG [here](https://github.com/encharm/Font-Awesome-SVG-PNG). New icons are first added to `vorta/assets/icons.collection.qrc` and then the command `pyrcc5 -o src/vorta/views/collection_rc.py src/vorta/assets/icons/collection.qrc` is run to compile them to a resource file, which is used by the UI files.

## Building Binaries
To build a macOS app package:
- add `Sparkle.framework` from [here](https://github.com/sparkle-project/Sparkle) and `borg` from [here](https://github.com/borgbackup/borg/releases) in `bin/macosx64`
- then uncomment or change the Apple signing profile to be used in `Makefile`
- finally run to `$ make Vorta.app` to build the app into the `dist` folder.

## Testing

Tests are in the folder `/tests`. Testing happens at the level of UI components. Calls to `borg` are mocked and can be replaced with some example json-output. To run tests:
```
$ pytest
```

To test for style errors:
```
$ flake8
```
