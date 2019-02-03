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

For UI icons, we use Fontawesome. You can browse available icons [here](https://fontawesome.com/icons) and download them as SVG [here](https://github.com/encharm/Font-Awesome-SVG-PNG). New icons are first added to both `src/vorta/assets/icons/dark/collection.qrc` and `src/vorta/assets/icons/light/collection.qrc`. Then, the command `make icon-resources` is run to compile them to a resource file which is used by the UI files.

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

## Translations

Translations are updated there: https://www.Transifex.com/borgbase/vorta/

### Policy for Translations

- No google translate or other automated translation.
- Only native or as-good-as-native speakers should translate.
- As there is a need for continued maintenance, a translator should be also a
  user of vorta, having some own interest in the translation (one-time
  translations are not that helpful if there is no one updating them regularly)
- A translation must have >90% translated strings. If a translation falls
  and stays below that for a longer time, it will not be used by vorta and
  ultimately, it will get removed from the repository also.

### Adding a New Language

- Only add a new language if you are willing to also update the translation
  in future, when new strings are added and existing strings change.
- Request a new language by opening a new issue on Github. We will then add it on Transifex.

### Updating a Language

- Please only work on a translation if you are a native speaker or you have
  similar language skills.
- Open a new issue on Github.
- Edit the language on Transifex.

### Using and Testing Transifex Translations

- Extract from source files (needed after most code changes to update line number):
  `make translations-from-source`
- Push to Transifex: `make translations-push`
- Pull finished translations from Transifex: `make translations-pull`
- Compile: `make translations-to-qm`
- Test with specific translation: `LANG=de vorta`
- Scale strings to test UI: `LANG=de TRANS_SCALE=200 vorta --foreground`

### Notes for Developers

- Original strings in `.ui` and `.py` must be American English (en_US) and ASCII.
- In English, not translated:
  - log messages (log file as well as log output on console or elsewhere)
  - other console output, print().
  - docs
  - py source code, comments, docstrings

- Translated:
  - GUI texts / messages

- In Qt (sub)classes, use self.tr("English string"), scope will
  be the instance class name.
- Elsewhere use vorta.i18n.translate("scopename", "English string")
- To only mark for string extraction, but not immediately translate,
  use vorta.i18n.trans_late function.
  Later, to translate, use vorta.i18n.translate (giving same scope).
  
### Style Guide/Glossary

- Headings, buttons and dropdowns are titleized: "Apply Changes"
- Field labels (same or next line) end with a colon and are titleized. "Allowed Networks:"
- No full stop `.` at the end of short labels, but when it's a full sentence.
- If something is in progress, use three dots (no ellipsis): "Starting backup..."
- **Repo/repository** = local or remote folder where Borg stores files.
- **Archive** (not snapshot) = result of `borg create` execution, an identifier to find a
  collection of files in a repo, as they existed at a past point in time.

### Required Software

To successfully run the translation-related Makefile targets, the translations
maintainer needs:

- `make` tool
- `pylupdate5` (from PyQt)
- `lrelease` (from Qt package)
- `tx` Transifex client (PyPI package `transifex-client`, contained in requirements.d/dev.txt)

Install on Debian 9 "Stretch":
```
$ apt install qttools5-dev-tools pyqt5-dev-tools
```

Install on macOS via Homebrew:
```
$ cd requirements.d && brew bundle
```
