import sys
import os
from vorta.models import SettingsModel


def get_updater():
    if sys.platform == 'darwin' and getattr(sys, 'frozen', False):
        """
        Use Sparkle framework on macOS.

        Settings: https://sparkle-project.org/documentation/customization/
        Examples: https://programtalk.com/python-examples/objc.loadBundle/

        To debug:
        $ defaults read com.borgbase.client.macos
        """

        import objc
        import Cocoa
        bundle_path = os.path.join(os.path.dirname(sys.executable), os.pardir, 'Frameworks', 'Sparkle.framework')
        objc.loadBundle('Sparkle', globals(), bundle_path)
        sparkle = SUUpdater.sharedUpdater()  # noqa: F821

        # A default Appcast URL is set in vorta.spec, when setting it here it's saved to defaults,
        # so we need both cases.
        if SettingsModel.get(key='updates_include_beta').value:
            appcast_nsurl = Cocoa.NSURL.URLWithString_('https://borgbase.github.io/vorta/appcast-pre.xml')
        else:
            appcast_nsurl = Cocoa.NSURL.URLWithString_('https://borgbase.github.io/vorta/appcast.xml')

        sparkle.setFeedURL_(appcast_nsurl)

        if SettingsModel.get(key='check_for_updates').value:
            sparkle.setAutomaticallyChecksForUpdates_(True)
            sparkle.checkForUpdatesInBackground()

        sparkle.setAutomaticallyDownloadsUpdates_(False)
        return sparkle

    else:  # TODO: implement for Linux
        return None
