"""Compatibility fallbacks for PyQt6 and Picard in headless/unit testing environments."""

from typing import Any

try:
    from PyQt6 import QtCore, QtGui, QtWidgets
except ImportError:
    class QtCore:  # type: ignore[no-redef]
        class QObject:
            def __init__(self, parent=None):
                self._parent = parent

        class QEvent:
            class Type:
                MouseButtonRelease = 3

        class Qt:
            class MouseButton:
                NoButton = 0
                LeftButton = 1
                RightButton = 2
                MiddleButton = 4

    class _FallbackCursor:
        @staticmethod
        def pos():
            return None

    class QtGui:  # type: ignore[no-redef]
        QCursor = _FallbackCursor

        class QActionGroup:
            def __init__(self, *args, **kwargs):
                pass

            def setExclusive(self, exclusive):
                pass

            def addAction(self, action):
                pass

    class _FallbackFont:
        def __init__(self):
            self._bold = False
            self._underline = False

        def setBold(self, value):
            self._bold = bool(value)

        def setUnderline(self, value):
            self._underline = bool(value)

        def bold(self):
            return self._bold

        def underline(self):
            return self._underline

    class _FallbackSignal:
        def __init__(self):
            self.callback = None

        def connect(self, callback):
            self.callback = callback

        def emit(self, *args):
            if self.callback:
                self.callback(*args)

    class _FallbackAction:
        def __init__(self, text):
            self.text = text
            self.checked = False
            self.checkable = False
            self.enabled = True
            self.triggered = _FallbackSignal()
            self._font = _FallbackFont()
            self._data = None

        def setCheckable(self, value):
            self.checkable = value

        def setChecked(self, value):
            self.checked = value

        def setEnabled(self, enabled):
            self.enabled = bool(enabled)

        def setToolTip(self, text):
            self.tooltip = text

        def setData(self, data):
            self._data = data

        def data(self):
            return self._data

        def font(self):
            return self._font

        def setFont(self, font):
            self._font = font

        def trigger(self):
            self.triggered.emit(False)

    class _FallbackMenu:
        selected_action = None

        def __init__(self, *args, **kwargs):
            self.actions = []
            self.parent = args[0] if args else None
            self.event_filters = []

        def addAction(self, text):
            action = _FallbackAction(text)
            self.actions.append(action)
            return action

        def addSeparator(self):
            self.actions.append(None)

        def setToolTipsVisible(self, visible):
            self.tooltips_visible = bool(visible)

        def installEventFilter(self, filter_obj):
            self.event_filters.append(filter_obj)

        def actionAt(self, pos):
            return self.selected_action

        def close(self):
            pass

        def exec(self, *args):
            return self.selected_action

        def deleteLater(self):
            pass

    class QtWidgets:  # type: ignore[no-redef]
        QMenu = _FallbackMenu

try:
    from picard import config
    from picard.debug_opts import DebugOpt
    from picard.plugin3.api import (
        Album,
        BaseAction,
        Metadata,
        PluginApi,
        Track,
        t_,
    )
except ImportError:
    config = None  # type: ignore[assignment]

    class DebugOpt:
        PLUGIN_DEVELOPMENT = "plugin-development"

    def t_(key: str, text: str | None = None, plural: str | None = None) -> str | tuple[str, str, str]:  # type: ignore[no-redef]
        if plural is not None:
            return (key, text or "", plural)
        return key

    _Base = QtCore.QObject if hasattr(QtCore, 'QObject') else object

    class BaseAction(_Base):  # type: ignore[no-redef]
        api: Any = None

        def __init__(self, parent=None):
            super().__init__(parent)
            self.tagger = getattr(self.api, 'tagger', None)
            self._menu = None
            self._enabled = True
            if not hasattr(self, 'destroyed') or not hasattr(self.destroyed, 'connect'):
                self.destroyed = _FallbackSignal()

        def setMenu(self, menu):
            self._menu = menu

        def menu(self):
            return self._menu

        def setEnabled(self, enabled):
            self._enabled = bool(enabled)

        def isEnabled(self):
            return self._enabled

    class PluginApi:  # type: ignore[no-redef]
        pass

    class Album:  # type: ignore[no-redef]
        pass

    class Track:  # type: ignore[no-redef]
        pass

    class Metadata:  # type: ignore[no-redef]
        pass


__all__ = [
    "Album",
    "BaseAction",
    "DebugOpt",
    "Metadata",
    "PluginApi",
    "QtCore",
    "QtGui",
    "QtWidgets",
    "Track",
    "config",
    "t_",
]
