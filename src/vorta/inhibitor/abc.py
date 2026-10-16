import logging
import sys

logger = logging.getLogger(__name__)


class Inhibitor(object):
    """
    An interface for managing power management inhibitors.
    """

    @classmethod
    def get_inhibitor(cls, what: str) -> 'Inhibitor':
        if sys.platform == 'darwin':
            from .iokit import IOKitInhibitor

            return IOKitInhibitor(what)
        else:
            from .fdo import FdoInhibitor, UnsupportedException

            try:
                return FdoInhibitor(what)
            except UnsupportedException:
                logger.warning("systemd inhibitor not available", exc_info=True)
                return NullInhibitor(what)

    @classmethod
    def get_noop_inhibitor(cls) -> 'Inhibitor':
        return NullInhibitor("nothing")

    def __init__(self, name: str):
        self._name = name

    def __enter__(self):
        self.inhibit()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.uninhibit()

    def inhibit(self):
        """
        Activate the inhibitor.
        Inhibitors are not shared so implementations should track whatever internal state is necessary
        """
        raise NotImplementedError()

    def uninhibit(self):
        """Deactivate the inhibitor"""
        raise NotImplementedError()


class NullInhibitor(Inhibitor):
    """Dummy implementation, in case we don't have one for current platform."""

    def __init__(self, name: str):
        super().__init__(name)

    def inhibit(self):
        pass

    def uninhibit(self):
        pass
