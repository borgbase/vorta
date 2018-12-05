import sys
import os
from vorta.models import SettingsModel


def get_updater():
    if sys.platform == 'darwin' and getattr(sys, 'frozen', False):
        # Use sparkle framework on macOS.
        # Examples: https://programtalk.com/python-examples/objc.loadBundle/
        from objc import loadBundle
        bundle_path = os.path.join(os.path.dirname(sys.executable), os.pardir, 'Frameworks', 'Sparkle.framework')
        loadBundle('Sparkle', globals(), bundle_path)
        sparkle = SUUpdater.sharedUpdater()  # noqa: F821
        if SettingsModel.get(key='updates_include_beta').value:
            sparkle.SharedUpdater.FeedURL = 'https://borgbase.github.io/vorta/appcast-pre.xml'

        if SettingsModel.get(key='check_for_updates').value:
            sparkle.setAutomaticallyChecksForUpdates_(True)
            sparkle.checkForUpdatesInBackground()

        sparkle.setAutomaticallyDownloadsUpdates_(False)
        return sparkle

    else:  # TODO: implement for Linux
        return None
