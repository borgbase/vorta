Appcasts for Vorta

This branch includes a Python script to generate and host 
[Appcast XML files](https://sparkle-project.org/documentation/publishing/)
used by Sparkle for macOS updates.

## Usage

First generate XML files:
```
python generate_appcast.py --include-prereleases appcast-pre.xml
python generate_appcast.py appcast.xml
```

Then push this branch to publish them at `https://borgbase.github.io/vorta/appcast.xml`