"""Options page for user configuration of pseudo-release features."""

from typing import (
    Any,
    ClassVar,
)

try:
    from PyQt6 import QtWidgets
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
            self.clicked = _DummySignal()
            self.linkActivated = _DummySignal()

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

        def setOpenExternalLinks(self, enabled):
            pass

        def text(self):
            return self._text

        def setText(self, text):
            self._text = str(text)

        def title(self):
            return self._text

        def addButton(self, *args):
            pass

    class QtWidgets:  # type: ignore[no-redef]
        QWidget = _DummyWidget
        QVBoxLayout = _DummyWidget
        QHBoxLayout = _DummyWidget
        QLabel = _DummyWidget
        QCheckBox = _DummyWidget
        QPushButton = _DummyWidget
        QGroupBox = _DummyWidget
        QFrame = _DummyWidget

try:
    from picard.plugin3.api import (
        OptionsPage,
        PageOptionConfigs,
        t_,
    )
except ImportError:
    class OptionsPage(QtWidgets.QWidget):  # type: ignore[no-redef]
        NAME = ""
        TITLE = ""
        PARENT = None
        api: Any = None

    PageOptionConfigs = dict[str, Any]  # type: ignore[misc]

    def t_(key: str, text: str | None = None, plural: str | None = None) -> str:  # type: ignore[no-redef]
        return text or key


class PseudoReleaseOptionsPage(OptionsPage):
    """Picard Options page for configuring Pseudo-Release features."""

    NAME = "pseudo_releases"
    TITLE = "Pseudo-Releases"
    PARENT = "plugins"

    OPTIONS: ClassVar[PageOptionConfigs] = {}

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
        layout.setSpacing(12)

        # Header description with formatting and external documentation links
        info_text = self._tr(
            "ui.info_pseudo_releases",
            "MusicBrainz <a href=\"https://musicbrainz.org/doc/Style/Specific_types_of_releases/Pseudo-Releases\">"
            "pseudo-releases</a> contain alternate tracklists (such as transliterated or "
            "translated titles) linked to an original release via the "
            "<a href=\"https://musicbrainz.org/relationship/fc399d47-23a7-4c28-bfcf-0607a562b644\">"
            "transl-tracklisting</a> relationship.<br><br>"
            "When a pseudo-release is loaded, this plugin automatically supplements missing catalog metadata "
            "(<code>date</code>, <code>releasecountry</code>, <code>barcode</code>, <code>media</code>, "
            "<code>label</code>, and <code>catalognumber</code>) from the best-matched original release.<br><br>"
            "Additionally, the original release ID is made available to tagger scripts and file naming scripts "
            "via the hidden variable <code>%~original_musicbrainz_albumid%</code>.",
        )
        self.lbl_info = QtWidgets.QLabel(info_text, self)
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setOpenExternalLinks(True)
        layout.addWidget(self.lbl_info)

        # Group: Cover Art Integration
        self.group_cover_art = QtWidgets.QGroupBox(
            self._tr("ui.group_cover_art", "Cover Art Integration"),
            self,
        )
        cover_layout = QtWidgets.QVBoxLayout(self.group_cover_art)
        cover_layout.setSpacing(10)

        self.lbl_cover_art_description = QtWidgets.QLabel(
            self._tr(
                "ui.enable_cover_art_description",
                "Pseudo-releases are not supposed to have cover artwork in MusicBrainz. Artwork is fetched from the "
                "Cover Art Archive using the linked original release MBID.",
            ),
            self.group_cover_art,
        )
        self.lbl_cover_art_description.setWordWrap(True)
        cover_layout.addWidget(self.lbl_cover_art_description)

        # Navigation row: Clean Push Button Style
        row_nav_layout = QtWidgets.QHBoxLayout()
        row_nav_layout.setSpacing(10)

        self.lbl_cover_art_note = QtWidgets.QLabel(
            self._tr(
                "ui.cover_art_note",
                "Provider order and enablement are configured under <b>Options &gt; Cover Art &gt; Providers</b>.",
            ),
            self.group_cover_art,
        )
        self.lbl_cover_art_note.setWordWrap(True)
        row_nav_layout.addWidget(self.lbl_cover_art_note, 1)

        self.btn_open_cover_providers = QtWidgets.QPushButton(
            self._tr(
                "ui.open_cover_providers",
                "Configure Providers...",
            ),
            self.group_cover_art,
        )
        self.btn_open_cover_providers.clicked.connect(self._open_cover_providers_page)
        row_nav_layout.addWidget(self.btn_open_cover_providers, 0)
        cover_layout.addLayout(row_nav_layout)

        layout.addWidget(self.group_cover_art)

        layout.addStretch()

    def _open_cover_providers_page(self):
        """Navigate directly to Picard's native Cover Art options page if hosted inside OptionsDialog."""
        dialog = getattr(self, 'dialog', None)
        if not dialog:
            # Fallback check on parent hierarchy
            parent = self.parent()
            while parent:
                if hasattr(parent, 'pagename_to_item'):
                    dialog = parent
                    break
                parent = parent.parent() if hasattr(parent, 'parent') else None

        if dialog and hasattr(dialog, 'pagename_to_item') and hasattr(dialog, 'ui'):
            item = dialog.pagename_to_item.get('cover')
            if item and hasattr(dialog.ui, 'pages_tree'):
                dialog.ui.pages_tree.setCurrentItem(item)

    def load(self):
        """Load settings from plugin configuration into UI widgets."""
        pass

    def save(self):
        """Save settings from UI widgets into plugin configuration."""
        pass
