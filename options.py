"""Options page for user configuration of pseudo-release features."""

from typing import Any

try:
    from PyQt6 import QtWidgets
    from picard.plugin3.api import (
        OptionsPage,
        t_,
    )
except ImportError:
    # Stubs for headless testing environments without PyQt6
    class _DummySignal:
        def __init__(self):
            self._callbacks = []

        def connect(self, callback):
            self._callbacks.append(callback)

        def emit(self, *args):
            for callback in self._callbacks:
                callback(*args)

    class _DummyWidget:
        def __init__(self, *args, **kwargs):
            self._checked = False
            self._enabled = True
            self._text = args[0] if args and isinstance(args[0], str) else ""
            self.toggled = _DummySignal()

        def setStyleSheet(self, *args):
            pass

        def setLayout(self, *args):
            pass

        def addWidget(self, *args):
            pass

        def addLayout(self, *args):
            pass

        def addStretch(self, *args):
            pass

        def setContentsMargins(self, *args):
            pass

        def setSpacing(self, *args):
            pass

        def isChecked(self):
            return self._checked

        def setChecked(self, val):
            checked = bool(val)
            if checked != self._checked:
                self._checked = checked
                self.toggled.emit(checked)

        def setEnabled(self, enabled):
            self._enabled = bool(enabled)

        def isEnabled(self):
            return self._enabled

        def setWordWrap(self, enabled):
            pass

        def text(self):
            return self._text

        def addButton(self, *args):
            pass

    class QtWidgets:  # type: ignore[no-redef]
        QWidget = _DummyWidget
        QVBoxLayout = _DummyWidget
        QLabel = _DummyWidget
        QCheckBox = _DummyWidget

    class OptionsPage(QtWidgets.QWidget):  # type: ignore[no-redef]
        NAME = ""
        TITLE = ""
        api: Any = None

    def t_(key: str, text: str | None = None, plural: str | None = None) -> str:  # type: ignore[no-redef]
        return text or key

try:
    from .constants import (
        OPT_AUTO_SUPPLEMENT,
        get_config_value,
    )
except (ImportError, ValueError):
    from constants import (
        OPT_AUTO_SUPPLEMENT,
        get_config_value,
    )


class PseudoReleaseOptionsPage(OptionsPage):
    """Picard Options page for configuring Pseudo-Release features."""

    NAME = "pseudo_releases"
    TITLE = "Pseudo-Releases"

    def _tr(self, key: str, text: str) -> str:
        """Translate text if Picard API tr is available, otherwise return default text."""
        api = getattr(self, 'api', None)
        if api and hasattr(api, 'tr'):
            try:
                res = api.tr(key, text)
                if res:
                    return res
            except Exception:
                pass
        return text

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        self.cb_auto_supplement = QtWidgets.QCheckBox(
            self._tr(
                "ui.auto_supplement",
                "Supplement pseudo-releases with original catalog metadata and cover art",
            ),
            self,
        )
        layout.addWidget(self.cb_auto_supplement)
        self.lbl_auto_supplement_description = QtWidgets.QLabel(
            self._tr(
                "ui.auto_supplement_description",
                "Fills missing tags only: date, originaldate, releasecountry, barcode, media, label, catalognumber. Cover art comes from the linked original release.",
            ),
            self,
        )
        self.lbl_auto_supplement_description.setWordWrap(True)
        layout.addWidget(self.lbl_auto_supplement_description)
        layout.addStretch()

    def load(self):
        """Load settings from plugin configuration into UI widgets."""
        if not hasattr(self, 'api') or not self.api:
            return

        cfg = self.api.plugin_config
        self.cb_auto_supplement.setChecked(get_config_value(cfg, OPT_AUTO_SUPPLEMENT, True))

    def save(self):
        """Save settings from UI widgets into plugin configuration."""
        if not hasattr(self, 'api') or not self.api:
            return

        cfg = self.api.plugin_config
        cfg[OPT_AUTO_SUPPLEMENT] = self.cb_auto_supplement.isChecked()
