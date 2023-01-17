import enum
import logging
import sys
from dataclasses import dataclass
from pathlib import PurePath
from typing import Any, Callable, Dict, List, NewType, Optional, Sequence, Set
from PyQt5.QtCore import QMetaType, QObject, QVariant, pyqtSignal, pyqtSlot
from PyQt5.QtDBus import QDBus, QDBusConnection, QDBusInterface, QDBusMessage
from PyQt5.QtGui import QTextDocument
from PyQt5.QtWidgets import QApplication
from vorta import application
from vorta.store.models import SettingsModel
from vorta.utils import get_asset

logger = logging.getLogger(__name__)

Identifier = NewType("Identifier", object)  # notification id
ActionSlot = Callable[[Identifier, str], Any]  # (id, action)


class VortaNotifications:
    """
    Usage:

    notifier = Notifications.pick()()
    notifier.deliver('blah', 'blah blah')
    """

    @classmethod
    def pick(cls):
        if sys.platform == "darwin":
            return DarwinNotifications()
        elif QDBusConnection.sessionBus().isConnected():
            return DBusNotifications()
        else:
            logger.warning("could not pick valid notification class")
            return cls()

    def deliver(self, title: str, text: str, level: str = "info", slot: ActionSlot = None) -> Identifier:
        """
        Notify the user with the given notification attributes.

        Parameters
        ----------
        title : str
            The summary/header of the notification.
        text : str
            The body/text of the notification.
        level : str, optional
            The level of severity/interruption/urgency, by default 'info'
        slot : ActionSlot, optional
            The slot to call when the notification is clicked, by default None

        Returns
        -------
        Identifier
            The id of the notification delivered.
        """
        pass

    def cancel(self, notification_id: Identifier):
        """
        Close a notification already delivered.

        Parameters
        ----------
        notification_id : Identifier
            The id of the notification to revoke.
        """
        pass

    def notifications_suppressed(self, level):
        """Decide if notification is sent or not based on settings and level."""
        if not SettingsModel.get(key="enable_notifications").value:
            logger.debug("notifications suppressed")
            return True
        if level == 'info' and not SettingsModel.get(key='enable_notifications_success').value:
            logger.debug('success notifications suppressed')
            return True

        logger.debug("notification not suppressed")
        return False


# ----  MacOS Notifications --------------------------------------------------

if sys.platform == "darwin":
    import objc
    from Foundation import NSUUID, NSObject
    from UserNotifications import (
        UNAuthorizationOptions,
        UNMutableNotificationContent,
        UNNotificationInterruptionLevel,
        UNNotificationPresentationOptions,
        UNNotificationRequest,
        UNNotificationResponse,
        UNNotificationSound,
        UNTimeIntervalNotificationTrigger,
        UNUserNotificationCenter,
    )

    UNUserNotificationCenterDelegate = objc.protocolNamed("UNUserNotificationCenterDelegate")

    class InterruptionLevel(enum.Enum):
        """Urgency of a notification."""

        PASSIVE = 0
        ACTIVE = 1
        TIME_SENSITIVE = 2
        CRITICAL = 3  # Only available to special apps

    class NotificationDelegate(NSObject, protocols=[UNUserNotificationCenterDelegate]):
        """
        https://developer.apple.com/documentation/usernotifications/unusernotificationcenterdelegate?language=objc
        """

        def __init__(self, open_settings_slot, action_slot):
            self.open_settings_slot = open_settings_slot
            self.action_slot = action_slot

        def userNotificationCenter_openSettingsForNotification_(self, center, notification):
            self.open_settings_slot(notification)

        def userNotificationCenter_didReceiveNotificationResponse_withCompletionHandler_(
            self, center, response, completionHandler
        ):
            self.action_slot(response)
            completionHandler()

        def userNotificationCenter_willPresentNotification_withCompletionHandle_(
            self, center, notification, completionHandler
        ):
            # UNNotificationPresentationOptionAlert is deprecated in favor of
            # UNNotificationPresentationOptionBanner since MacOS 11+
            completionHandler(UNNotificationPresentationOptions.UNNotificationPresentationOptionAlert)

    class DarwinNotifications(VortaNotifications):
        """
        Notify via notification center and pyobjc bridge.

        https://developer.apple.com/documentation/usernotifications?language=occ
        """

        INTERRUPTION = {
            "info": InterruptionLevel.ACTIVE,
            "error": InterruptionLevel.TIME_SENSITIVE,
        }

        def __init__(self):
            self.notifications: Dict[str, ActionSlot] = {}
            self.app: application.VortaApp = QApplication.instance()

            self.center = UNUserNotificationCenter.currentNotificationCenter()
            self.center.setDelegate_(NotificationDelegate(self._receive_response, self._open_settings))

            # request silent permission
            self.center.requestAuthorizationWithOptions_completionHandler_(
                [
                    UNAuthorizationOptions.UNAuthorizationOptionProvisional,
                    UNAuthorizationOptions.UNAuthorizationOptionAlert,
                    UNAuthorizationOptions.UNAuthorizationOptionSound,
                    UNAuthorizationOptions.UNAuthorizationOptionProvidesAppNotificationSettings,
                ],
                self._process_authorization,
            )

            # declare notfications types and register actions
            # PASS actions are not implemented

        def _process_authorization(self, granted: bool, error):
            if not granted:
                error_description = error.localizedDescription()
                self.logger.error(f"Couldn't authorize notifications because of {error_description}")

        def _process_request(self, error):
            error_description = error.localizedDescription()
            self.logger.warning(f"Couldn't request notification because of {error_description}")

        def _receive_response(self, response):
            notification_id = response.notification().request().identifier()
            action = response.actionIdentifier()

            if action == UNNotificationResponse.UNNotificationDefaultActionIdentifier:
                # default action when clicking on the notification
                logger.debug(f"Default action of {notification_id} invoked.")
                if notification_id in self.notifications:
                    slot = self.notifications[notification_id]
                    slot(notification_id, "default")
            else:
                # Other actions aren't supported yet.
                pass

        def _open_settings(self, notification):
            self.app.open_main_window_action()
            self.app.main_window.open_misc_tab()

        def _request(
            self,
            title: str,
            body: str,
            level: InterruptionLevel = InterruptionLevel.ACTIVE,
            slot: Optional[ActionSlot] = None,
        ) -> Identifier:

            logger.debug("Send MacOS notification with" + f" title={title}, body={body}, level={level}.")

            # prepare arguments
            if level == InterruptionLevel.PASSIVE:
                interruption = UNNotificationInterruptionLevel.UNNotificationInterruptionLevelPassive
            elif level == InterruptionLevel.ACTIVE:
                interruption = UNNotificationInterruptionLevel.UNNotificationInterruptionLevelActive
            else:
                interruption = UNNotificationInterruptionLevel.UNNotificationInterruptionLevelTimeSensitive

            # create and post notification
            content = UNMutableNotificationContent.alloc().init()
            content.setTile_(title)
            content.setBody_(body)
            content.setSound_(UNNotificationSound.defaultSound())
            content.setInterruptionLevel_(interruption)

            trigger = UNTimeIntervalNotificationTrigger.triggerWithTimeInterval_repeats_(1, False)

            notification_id = NSUUID.UUID().uuidString()
            request = UNNotificationRequest.requestWithIdentifier_content_trigger_(notification_id, content, trigger)

            self.center.addNotificationRequest_withCompletionHandler_(request, self._process_request)

            if slot:
                self.notifications[notification_id] = slot
            elif notification_id in self.notifications:
                del self.notifications[notification_id]

            return notification_id

        def cancel(self, notification_id: Identifier):
            self.center.removePendingNotificationRequestsWithIdentifiers_([notification_id])
            self.center.removeDeliveredNotificationsWithIdentifiers_([notification_id])

            self.notifications.pop(notification_id, None)

        def deliver(self, title, text, level="info", slot=None):
            if self.notifications_suppressed(level):
                return

            return self._request(title, text, level=self.INTERRUPTION[level], slot=slot)


# ---- DBus notifications ----------------------------------------------------


class Urgency(enum.Enum):
    """
    The urgency levels of a notification.
    """

    # On KDE notifications of a low urgency aren't kept in the notification
    # history.
    LOW = 0
    NORMAL = 1
    # Critical notification usually do not timeout.
    CRITICAL = 2


class CloseReason(enum.Enum):
    """Reasons for a notification being closed."""

    EXPIRED = 1
    DISMISSED = 2
    DBUS_REQUEST = 3
    UNDEFINED = 4


@dataclass
class Action:
    """An action that is displayed as part of a notification."""

    #: the translated label for the action
    label: str
    #: the freedesktop conform icon identifier
    icon: Optional[str] = None
    #: the slot to call
    slot: Optional[ActionSlot] = None

    @property
    def key(self) -> Optional[str]:
        """
        The identifier of this action.

        This is the same as the icon attribute since the key field is used to
        specify the icon. The key and the icon must be unique to their
        notification.
        """
        return self.icon

    @key.setter
    def key(self, value: str):
        self.icon = value

    def __repr__(self) -> str:
        return "<{}, {}>".format(self.key, self.label)


def qt_type(value, type):
    """Convert a python value to the given qt type."""
    variant = QVariant(value)
    variant.convert(type)
    return variant


class DBusNotifications(QObject, VortaNotifications):
    """
    Use QtDBus to send notifications.

    Uses the dbus service described in the freedesktop.org specifications:
    https://specifications.freedesktop.org/notification-spec/latest/

    """

    # dbus interface identifiers
    SERVICE = "org.freedesktop.Notifications"
    PATH = "/org/freedesktop/Notifications"
    INTERFACE = "org.freedesktop.Notifications"

    # notification specifics
    URGENCY = {"info": Urgency.NORMAL, "error": Urgency.CRITICAL}
    APP_NAME = "Vorta"  # human readable name
    APP_IDENTIFIER = "com.borgbase.Vorta"  # name of the .desktop file

    # signals
    actionInvoked = pyqtSignal(int, str)
    notificationClosed = pyqtSignal(int, int)

    def __init__(self):
        """Init."""
        super().__init__()
        self.flags: Set[str] = set()
        self.notifications: Dict[Dict[str, ActionSlot]] = {}

        # retrieve server capabilities
        self.bus = QDBusConnection.sessionBus()
        self.interface = QDBusInterface(self.SERVICE, self.PATH, self.INTERFACE, self.bus, self)
        if self.interface.isValid():
            reply = self.interface.call(QDBus.AutoDetect, "GetCapabilities")
            if reply.errorName():
                logger.warning("Requesting server capabilities failed" + f" because of {reply.errorMessage()}")
            else:
                self.flags = set(reply.arguments()[0])
                logger.debug("DBus Notification server capabilites: " + ", ".join(self.flags))
        else:
            logger.warning("{} is not a valid dbus interface.".format(self.INTERFACE))

        # connect to dbus signals
        self.bus.connect(
            "",
            "",
            self.INTERFACE,
            "NotificationClosed",
            "uu",
            self._notification_closed,
        )
        self.bus.connect("", "", self.INTERFACE, "ActionInvoked", "us", self._action_invoked)

    @pyqtSlot(QDBusMessage)
    def _notification_closed(self, msg: QDBusMessage):
        notification_id, reason = msg.arguments()

        if notification_id in self.notifications:
            del self.notifications[notification_id]

        logger.debug("Notification {} closed.".format(notification_id))
        self.notificationClosed.emit(notification_id, reason)

    @pyqtSlot(QDBusMessage)
    def _action_invoked(self, msg: QDBusMessage):
        notification_id, action = msg.arguments()

        if notification_id not in self.notifications:
            return

        slots = self.notifications[notification_id]
        if action in slots:
            slot = slots[action]

            # for some reason the signal will be received twice
            # this will ensure each action can only be called once
            del slots[action]

            slot(notification_id, action)

        logger.debug(f"Action {action} of {notification_id} invoked.")
        self.actionInvoked.emit(notification_id, action)

    def _notify(
        self,
        summary: str,
        body: str,
        urgency: Urgency = Urgency.NORMAL,
        category: str = "",
        actions: Sequence[Action] = [],
        label: str = "",
        slot: Optional[ActionSlot] = None,
        replace_id: int = 0,
    ) -> int:
        """
        Send a notification over the freedesktop dbus interface.

        The default action is usually triggered when clicking on a
        notification. Its label may or may not be displayed.
        By default no notification will be replaced.

        Parameters
        ----------
        summary : str
            The title/header line.
        body : str
            The notification text.
        urgency : Urgency, optional
            The level of importance, by default Urgency.NORMAL
        category : str, optional
            The category of the notification, by default ''
        actions : Sequence[Action], optional
            A list of up to three actions to accessible
            through the notification, by default []
        label : str, optional
            The label of the default action, by default ''
        slot : Optional[ActionSlot], optional
            The slot for default action, by default None
        replace_id : int, optional
            The notification to update, by default 0
        """
        logger.debug(
            "Send notification over DBus with "
            + f"summary={summary}, urgency={urgency}, "
            + f"category={category} and actions={actions}"
        )

        # notification arguments
        app_name = self.APP_NAME
        notification_id = replace_id
        icon = self.APP_IDENTIFIER
        hints = {
            "urgency": urgency.value,
            "desktop-entry": self.APP_IDENTIFIER,
            "action-icons": True,
            "category": category,
            "image-path": PurePath(get_asset("icons/icon.svg")).as_uri(),
        }
        time = -1  # unset

        # process actions
        if len(actions) > 3:
            logger.warning("To many actions for a notification.")

        action_list: List[str] = ["default", label] if label or slot else []
        for i, action in enumerate(actions):
            if not action.key:
                action.key = str(i)
            action_list.append(action.key)
            action_list.append(action.label)

        # prepare arguments
        if "body-markup" not in self.flags:
            # strip markup
            body = QTextDocument(body).toPlainText()

        # send notification
        if not self.interface.isValid():
            logger.warning("Invalid dbus interface")
            return

        reply = self.interface.call(
            QDBus.CallMode.AutoDetect,  # autodetect reply
            "Notify",  # method
            app_name,
            qt_type(notification_id, QMetaType.Type.UInt),
            icon,
            summary,
            body,
            qt_type(action_list, QMetaType.QStringList),
            qt_type(hints, QMetaType.Type.QVariantMap),
            time,
        )

        if reply.errorName():
            logger.warning(reply.errorMessage())
            return 0

        # save 'slots'
        notification_id = reply.arguments()[0]
        slots = self.notifications[notification_id] = {}  # replace slots
        if slot:
            slots["default"] = slot
        for action in actions:
            if action.slot:
                slots[action.key] = action.slot

        return notification_id

    @pyqtSlot(int)
    def cancel(self, notification_id: int):
        """Close the notification with the given id."""
        notification_id = qt_type(notification_id, QMetaType.Type.UInt)

        self.interface.call(QDBus.CallMode.AutoDetect, "CloseNotification", notification_id)

    def deliver(self, title, text, level="info") -> int:
        if self.notifications_suppressed(level):
            return -1

        return self._notify(
            title,
            text,
            urgency=self.URGENCY[level],
            slot=lambda *args: QApplication.instance().open_main_window_action(),
        )
