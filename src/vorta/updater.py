import os
import sys

from vorta.store.models import SettingsModel


def get_updater():
    if sys.platform == 'darwin' and getattr(sys, 'frozen', False):
        """
        Use Sparkle framework on macOS.

        Settings: https://sparkle-project.org/documentation/customization/
        Examples: https://programtalk.com/python-examples/objc.loadBundle/

        To debug:
        $ defaults read com.borgbase.client.macos
        """

        import Cocoa
        import objc

        bundle_path = os.path.join(
            os.path.dirname(sys.executable),
            os.pardir,
            'Frameworks',
            'Sparkle.framework',
        )
        # Only load the framework. The default class scan (`scan_classes=True`) wraps every
        # Objective-C class in the process (tens of thousands) as a Python class and keeps
        # them in this module's globals for the lifetime of the app, costing well over 100 MB.
        objc.loadBundle('Sparkle', globals(), bundle_path, scan_classes=False)
        sparkle = objc.lookUpClass('SUUpdater').sharedUpdater()

        # A default Appcast URL is set in vorta.spec, when setting it here it's saved to defaults,
        # so we need both cases.
        if SettingsModel.get(key='updates_include_beta').value:
            appcast_nsurl = Cocoa.NSURL.URLWithString_('https://borgbase.github.io/vorta/appcast-pre.xml')
        else:
            appcast_nsurl = Cocoa.NSURL.URLWithString_('https://borgbase.github.io/vorta/appcast.xml')

        sparkle.setFeedURL_(appcast_nsurl)

        # Sparkle persists this in user defaults, so it must also be turned off explicitly.
        check_for_updates = bool(SettingsModel.get(key='check_for_updates').value)
        sparkle.setAutomaticallyChecksForUpdates_(check_for_updates)
        if check_for_updates:
            sparkle.checkForUpdatesInBackground()

        sparkle.setAutomaticallyDownloadsUpdates_(False)
        return sparkle

    else:  # TODO: implement for Linux
        return None
