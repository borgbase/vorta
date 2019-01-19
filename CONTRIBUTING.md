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
Qt Creator is used to edit views. Install from [their site](https://www.qt.io/download) or using Homebrew and then open the .ui files in `vorta/assets/UI` with Qt Creator:
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

## Working with translations

NOTE: we are currently still working on the original strings.
      DO NO TRANSLATION WORK EXCEPT IF YOU ARE WILLING TO DO DOUBLE WORK.

Translations are updated there: https://www.transifex.com/borgbase/vorta/

### Policy for translations

- no google translate or other automated translation.
- only native or as-good-as-native speakers should translate.
- as there is a need for continued maintenance, a translator should be also a
  user of vorta, having some own interest in the translation (one-time
  translations are not that helpful if there is noone updating them regularly)
- a translation must have >90% translated strings. if a translation falls
  and stays below that for a longer time, it will not be used by vorta and
  ultimately, it will get removed from the repository also.

### Adding a new language

- Only add a new language if you are willing to also update the translation
  in future, when new strings are added and existing strings change.
- Request a new language via transifex.
- TODO: add notes here what the maintainer has to do

### Updating a language

- Please only work on a translation if you are a native speaker or you have
  similar language skills.
- Edit the language on transifex.

### Data Flow to/from transifex

- extract: make translations-from-source
- push: make translations-push
- pull: make translations-pull
- compile: make translations-to-qm


### Notes for developers

- original strings in .ui and .py must be American English (en_US)
- in English, not translated:

  - log messages (log file as well as log output on console or elsewhere)
  - other console output, print().
  - docs
  - py source code, comments, docstrings
- translated:

  - GUI texts / messages
- in Qt (sub)classes, use self.tr("English string"), scope will
  be the instance class name.
- elsewhere use vorta.i18n.translate("scopename", "English string")
- to only mark for string extraction, but not immediately translate,
  use vorta.i18n.trans_late function.
  Later, to translate, use vorta.i18n.translate (giving same scope).

### Required Software

To successfully run the translation-related Makefile targets, the translations
maintainer needs:

- make tool
- pylupdate5
- lrelease
- transifex-client pypi package
  (should be already there via requirements.d/dev.txt)

Debian 9 "Stretch":

apt install qttools5-dev-tools pyqt5-dev-tools
