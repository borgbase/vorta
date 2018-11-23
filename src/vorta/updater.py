import sys
import os


def get_updater():
    if sys.platform == 'darwin' and getattr(sys, 'frozen', False):
        # Use sparkle framework on macOS.
        # Examples: https://programtalk.com/python-examples/objc.loadBundle/
        from objc import loadBundle
        bundle_path = os.path.join(os.path.dirname(sys.executable), os.pardir, 'Frameworks', 'Sparkle.framework')
        loadBundle('Sparkle', globals(), bundle_path)
        sparkle = SUUpdater.sharedUpdater()  # noqa: F821
        sparkle.setAutomaticallyChecksForUpdates_(True)
        sparkle.setAutomaticallyDownloadsUpdates_(False)
        sparkle.checkForUpdatesInBackground()
        return sparkle

    else:  # TODO: implement for Linux
        return None
