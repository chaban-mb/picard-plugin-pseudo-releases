"""Mock Qt classes for isolated headless test environments without PyQt6."""

from typing import Any


class _DummySignal:
    """Minimal Qt signal mock providing connect and emit."""

    def __init__(self) -> None:
        self._callbacks: list[Any] = []

    def connect(self, callback: Any) -> None:
        self._callbacks.append(callback)

    def emit(self, *args: Any) -> None:
        for callback in self._callbacks:
            callback(*args)


class _FallbackCursor:
    """Mock QCursor."""

    @staticmethod
    def pos() -> None:
        return None


class _FallbackFont:
    """Mock QFont."""

    def __init__(self) -> None:
        self._bold = False
        self._underline = False

    def setBold(self, value: bool) -> None:
        self._bold = bool(value)

    def setUnderline(self, value: bool) -> None:
        self._underline = bool(value)

    def bold(self) -> bool:
        return self._bold

    def underline(self) -> bool:
        return self._underline


class _FallbackAction:
    """Mock QAction."""

    def __init__(self, text: str = "") -> None:
        self.text = text
        self.checked = False
        self.checkable = False
        self.enabled = True
        self.triggered = _DummySignal()
        self._font = _FallbackFont()
        self._data: Any = None
        self.tooltip = ""

    def setCheckable(self, value: bool) -> None:
        self.checkable = bool(value)

    def setChecked(self, value: bool) -> None:
        self.checked = bool(value)

    def setEnabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)

    def setToolTip(self, text: str) -> None:
        self.tooltip = str(text)

    def setData(self, data: Any) -> None:
        self._data = data

    def data(self) -> Any:
        return self._data

    def font(self) -> _FallbackFont:
        return self._font

    def setFont(self, font: _FallbackFont) -> None:
        self._font = font

    def trigger(self) -> None:
        self.triggered.emit(False)


class _DummyWidget:
    """Universal mock widget for PyQt6 widget types."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._checked = False
        self._enabled = True
        self._text = args[0] if args and isinstance(args[0], str) else ""
        self.toggled = _DummySignal()
        self.clicked = _DummySignal()
        self.linkActivated = _DummySignal()
        self._parent = args[0] if args and isinstance(args[0], _DummyWidget) else kwargs.get("parent")

    def setStyleSheet(self, *args: Any) -> None:
        pass

    def setLayout(self, *args: Any) -> None:
        pass

    def addWidget(self, *args: Any) -> None:
        pass

    def addLayout(self, *args: Any) -> None:
        pass

    def addStretch(self, *args: Any) -> None:
        pass

    def setContentsMargins(self, *args: Any) -> None:
        pass

    def setSpacing(self, *args: Any) -> None:
        pass

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, val: bool) -> None:
        checked = bool(val)
        if checked != self._checked:
            self._checked = checked
            self.toggled.emit(checked)

    def setEnabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)

    def isEnabled(self) -> bool:
        return self._enabled

    def setWordWrap(self, enabled: bool) -> None:
        pass

    def setOpenExternalLinks(self, enabled: bool) -> None:
        pass

    def text(self) -> str:
        return self._text

    def setText(self, text: Any) -> None:
        self._text = str(text)

    def title(self) -> str:
        return self._text

    def addButton(self, *args: Any) -> None:
        pass

    def parent(self) -> Any:
        return self._parent


class _FallbackMenu(_DummyWidget):
    """Mock QMenu."""

    selected_action: Any = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.actions_list: list[Any] = []
        self.event_filters: list[Any] = []
        self.tooltips_visible = False

    def actions(self) -> list[Any]:
        return list(self.actions_list)

    def addAction(self, text: str) -> _FallbackAction:
        action = _FallbackAction(text)
        self.actions_list.append(action)
        return action

    def addSeparator(self) -> None:
        self.actions_list.append(None)

    def setToolTipsVisible(self, visible: bool) -> None:
        self.tooltips_visible = bool(visible)

    def installEventFilter(self, filter_obj: Any) -> None:
        self.event_filters.append(filter_obj)

    def actionAt(self, pos: Any) -> Any:
        return self.selected_action

    def close(self) -> None:
        pass

    def exec(self, *args: Any) -> Any:
        return self.selected_action

    def deleteLater(self) -> None:
        pass


class MockQtCore:
    """Mock QtCore namespace."""

    class QObject:
        def __init__(self, parent: Any = None) -> None:
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

    class QPointF:
        def __init__(self, *args: Any) -> None:
            pass


class MockQtGui:
    """Mock QtGui namespace."""

    QCursor = _FallbackCursor
    QFont = _FallbackFont

    class QActionGroup:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def setExclusive(self, exclusive: bool) -> None:
            pass

        def addAction(self, action: Any) -> None:
            pass


class MockQtWidgets:
    """Mock QtWidgets namespace."""

    QWidget = _DummyWidget
    QVBoxLayout = _DummyWidget
    QHBoxLayout = _DummyWidget
    QLabel = _DummyWidget
    QCheckBox = _DummyWidget
    QPushButton = _DummyWidget
    QGroupBox = _DummyWidget
    QFrame = _DummyWidget
    QMenu = _FallbackMenu

    class QApplication:
        _instance: Any = None

        def __init__(self, *args: Any) -> None:
            MockQtWidgets.QApplication._instance = self

        @classmethod
        def instance(cls) -> Any:
            return cls._instance
