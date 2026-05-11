import logging
import os
from ctypes import byref, c_uint32

import objc
from Foundation import NSString

from vorta.inhibitor.abc import Inhibitor

logger = logging.getLogger(__name__)

iokit = objc.loadBundle('IOKit', bundle_path='/System/Library/Frameworks/IOKit.framework', module_globals=globals())

objc.loadBundleFunctions(
    iokit,
    globals(),
    [
        (
            'IOPMAssertionCreateWithName',
            # https://developer.apple.com/documentation/iokit/1557134-iopmassertioncreatewithname
            b'i@I@o^I',
        ),
        (
            'IOPMAssertionRelease',
            # https://developer.apple.com/documentation/iokit/1557090-iopmassertionrelease
            b'iI',
        ),
    ],
)


def create_pm_assertion(name: str) -> int | None:
    try:
        result, assertion = IOPMAssertionCreateWithName(  # noqa: F821
            'PreventUserIdleSystemSleep',
            255,  # https://developer.apple.com/documentation/iokit/1557096-assertion/kiopmassertionlevelon
            name,
            None,
        )
        if result == 0:
            return assertion
        else:
            logger.warning(f'IOPMAssertionCreateWithName failed with code {result}')
            return None
    except Exception as e:
        logger.error(f'Failed to create sleep assertion: {e}')
        return None


def release_pm_assertion(assertion_id: int):
    try:
        result = IOPMAssertionRelease(assertion_id)  # noqa: F821
        if result != 0:
            logger.warning(f'IOPMAssertionRelease failed with code {result}')
    except Exception as e:
        logger.error(f'Failed to release sleep assertion: {e}')


class IOKitInhibitor(Inhibitor):
    def __init__(self, name: str):
        super().__init__(name)
        self.assertion_id = None

    def inhibit(self):
        self.assertion_id = create_pm_assertion(self._name)

    def uninhibit(self):
        if self.assertion_id is not None:
            release_pm_assertion(self.assertion_id)
            logger.info("Released sleep assertion with id %d", self.assertion_id)
            self.assertion_id = None
        else:
            logger.info("No active sleep assertion to release")
