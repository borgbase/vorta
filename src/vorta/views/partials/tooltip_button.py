from typing import Optional

from PyQt6.QtCore import QCoreApplication, QEvent, QSize, Qt
from PyQt6.QtGui import QHelpEvent, QIcon, QMouseEvent, QPaintEvent
from PyQt6.QtWidgets import QSizePolicy, QStyle, QStylePainter, QToolTip, QWidget


class ToolTipButton(QWidget):
    """
    A flat button showing a tooltip when the mouse moves over it.

    The default icon is `help-about`.

    Parameters
    ----------
    icon : QIcon, optional
        The icon to display, by default `help-about`
    parent : QWidget, optional
        The parent of this widget, by default None
    """

    def __init__(self, icon: Optional[QIcon] = None, parent: Optional[QWidget] = None) -> None:
        """
        Init.
        """
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.WhatsThisCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setMouseTracking(True)
        self._icon = icon or QIcon()

    def sizeHint(self) -> QSize:
        """
        Get the recommended size for the widget.

        Returns
        -------
        QSize

        See Also
        --------
        https://doc.qt.io/qt-5/qwidget.html#sizeHint-prop
        """
        size = self.style().pixelMetric(QStyle.PixelMetric.PM_ButtonIconSize)
        return QSize(size, size)

    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Repaint the widget on receiving a paint event.

        A paint event is a request to repaint all or part of a widget.
        It can happen for one of the following reasons:

        - repaint() or update() was invoked,
        - the widget was obscured and has now been uncovered, or
        - many other reasons.

        Many widgets can simply repaint their entire surface when asked to,
        but some slow widgets need to optimize by painting only the
        requested region: QPaintEvent::region().
        This speed optimization does not change the result,
        as painting is clipped to that region during event processing.
        QListView and QTableView do this, for example.

        Parameters
        ----------
        event : QPaintEvent
            The paint event

        See Also
        --------
        https://doc.qt.io/qt-5/qwidget.html#paintEvent
        """
        painter = QStylePainter(self)
        if self._icon:
            painter.drawPixmap(
                event.rect(),
                self._icon.pixmap(event.rect().size(), QIcon.Mode.Normal if self.isEnabled() else QIcon.Mode.Disabled),
            )
        painter.end()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        Process mouse move events for this widget.

        If mouse tracking is switched off, mouse move events only occur if a
        mouse button is pressed while the mouse is being moved.
        If mouse tracking is switched on, mouse move events occur even
        if no mouse button is pressed.

        Parameters
        ----------
        event : QMouseEvent
            The corresponding mouse event.

        See Also
        --------
        setMouseTracking
        https://doc.qt.io/qt-5/qwidget.html#mouseMoveEvent
        """
        super().mouseMoveEvent(event)
        QToolTip.showText(event.globalPosition().toPoint(), self.toolTip(), self)
        QCoreApplication.postEvent(
            self, QHelpEvent(QEvent.Type.ToolTip, event.position().toPoint(), event.globalPosition().toPoint())
        )

    def setIcon(self, icon: QIcon):
        """
        Set the icon displayed by the widget.

        This triggers a repaint event.

        Parameters
        ----------
        icon : QIcon
            The new icon.
        """
        self._icon = icon
        self.update()

    def icon(self) -> QIcon:
        """
        Get the icon displayed by the widget.

        Returns
        -------
        QIcon
            The current icon.
        """
        return self._icon
