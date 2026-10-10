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

try:
    from .constants import (
        OPT_AUTO_SUPPLEMENT,
        OPT_ENABLE_ORIGINAL_COVER_ART,
        OPT_PRESERVE_EXISTING_TAGS,
        OPT_SET_ORIGINAL_RELEASE_ID,
        OPT_SHOW_CONTEXT_MENU,
        get_config_value,
    )
except (ImportError, ValueError):
    from constants import (
        OPT_AUTO_SUPPLEMENT,
        OPT_ENABLE_ORIGINAL_COVER_ART,
        OPT_PRESERVE_EXISTING_TAGS,
        OPT_SET_ORIGINAL_RELEASE_ID,
        OPT_SHOW_CONTEXT_MENU,
        get_config_value,
    )


class PseudoReleaseOptionsPage(OptionsPage):
    """Picard Options page for configuring Pseudo-Release features."""

    NAME = "pseudo_releases"
    TITLE = "Pseudo-Releases"
    PARENT = "plugins"

    OPTIONS: ClassVar[PageOptionConfigs] = {
        OPT_AUTO_SUPPLEMENT: {'widgets': ['cb_auto_supplement']},
        OPT_PRESERVE_EXISTING_TAGS: {'widgets': ['cb_preserve_existing']},
        OPT_SET_ORIGINAL_RELEASE_ID: {'widgets': ['cb_set_original_tag']},
        OPT_ENABLE_ORIGINAL_COVER_ART: {'widgets': ['cb_enable_original_cover_art']},
        OPT_SHOW_CONTEXT_MENU: {'widgets': ['cb_show_context_menu']},
    }

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

        # Header description
        self.lbl_info = QtWidgets.QLabel(
            self._tr(
                "ui.info_pseudo_releases",
                "MusicBrainz pseudo-releases contain alternate tracklists (such as transliterated or "
                "translated titles) linked to an original physical release via the transl-tracklisting relationship.",
            ),
            self,
        )
        self.lbl_info.setWordWrap(True)
        layout.addWidget(self.lbl_info)

        # Group 1: Metadata Supplementation
        self.group_metadata = QtWidgets.QGroupBox(
            self._tr("ui.group_metadata", "Metadata Supplementation"),
            self,
        )
        meta_layout = QtWidgets.QVBoxLayout(self.group_metadata)
        meta_layout.setSpacing(6)

        self.cb_auto_supplement = QtWidgets.QCheckBox(
            self._tr(
                "ui.auto_supplement",
                "Automatically supplement catalog metadata",
            ),
            self.group_metadata,
        )
        meta_layout.addWidget(self.cb_auto_supplement)

        self.lbl_auto_supplement_description = QtWidgets.QLabel(
            self._tr(
                "ui.auto_supplement_description",
                "When loading a pseudo-release, populate date, originaldate, releasecountry, barcode, "
                "media, label, and catalognumber from the best-matched original release.",
            ),
            self.group_metadata,
        )
        self.lbl_auto_supplement_description.setWordWrap(True)
        meta_layout.addWidget(self.lbl_auto_supplement_description)

        # Indented sub-options container
        sub_widget = QtWidgets.QWidget(self.group_metadata)
        sub_layout = QtWidgets.QVBoxLayout(sub_widget)
        sub_layout.setContentsMargins(20, 4, 0, 0)
        sub_layout.setSpacing(6)

        self.cb_preserve_existing = QtWidgets.QCheckBox(
            self._tr(
                "ui.preserve_existing",
                "Preserve existing pseudo-release tags (fill missing only)",
            ),
            sub_widget,
        )
        sub_layout.addWidget(self.cb_preserve_existing)

        self.cb_set_original_tag = QtWidgets.QCheckBox(
            self._tr(
                "ui.set_original_tag",
                "Save linked original MBID as tag (~original_musicbrainz_albumid)",
            ),
            sub_widget,
        )
        sub_layout.addWidget(self.cb_set_original_tag)

        self.lbl_set_original_tag_description = QtWidgets.QLabel(
            self._tr(
                "ui.set_original_tag_description",
                "Enables tagger scripts and file naming patterns to reference the original release ID.",
            ),
            sub_widget,
        )
        self.lbl_set_original_tag_description.setWordWrap(True)
        sub_layout.addWidget(self.lbl_set_original_tag_description)

        meta_layout.addWidget(sub_widget)
        layout.addWidget(self.group_metadata)

        # Group 2: Cover Art Integration
        self.group_cover_art = QtWidgets.QGroupBox(
            self._tr("ui.group_cover_art", "Cover Art Integration"),
            self,
        )
        cover_layout = QtWidgets.QVBoxLayout(self.group_cover_art)
        cover_layout.setSpacing(6)

        self.cb_enable_original_cover_art = QtWidgets.QCheckBox(
            self._tr(
                "ui.enable_cover_art",
                "Retrieve cover artwork from linked original release",
            ),
            self.group_cover_art,
        )
        cover_layout.addWidget(self.cb_enable_original_cover_art)

        self.lbl_cover_art_description = QtWidgets.QLabel(
            self._tr(
                "ui.enable_cover_art_description",
                "Fetches artwork from the Cover Art Archive using the original release ID if the pseudo-release has none.",
            ),
            self.group_cover_art,
        )
        self.lbl_cover_art_description.setWordWrap(True)
        cover_layout.addWidget(self.lbl_cover_art_description)

        self.lbl_cover_art_note = QtWidgets.QLabel(
            self._tr(
                "ui.cover_art_note",
                "Note: Also ensure \"Cover Art Archive (via Original Release)\" is enabled in Options > Cover Art > Providers.",
            ),
            self.group_cover_art,
        )
        self.lbl_cover_art_note.setWordWrap(True)
        cover_layout.addWidget(self.lbl_cover_art_note)

        layout.addWidget(self.group_cover_art)

        # Group 3: Linked Original Editions
        self.group_context_menu = QtWidgets.QGroupBox(
            self._tr("ui.group_context_menu", "Linked Original Editions"),
            self,
        )
        menu_layout = QtWidgets.QVBoxLayout(self.group_context_menu)
        menu_layout.setSpacing(6)

        self.cb_show_context_menu = QtWidgets.QCheckBox(
            self._tr(
                "ui.show_context_menu",
                "Enable \"Linked original editions\" right-click context menu",
            ),
            self.group_context_menu,
        )
        menu_layout.addWidget(self.cb_show_context_menu)

        self.lbl_context_menu_description = QtWidgets.QLabel(
            self._tr(
                "ui.show_context_menu_description",
                "Allows manually choosing an alternative original release edition from the album context menu.",
            ),
            self.group_context_menu,
        )
        self.lbl_context_menu_description.setWordWrap(True)
        menu_layout.addWidget(self.lbl_context_menu_description)

        layout.addWidget(self.group_context_menu)

        # Cascade master toggle state across all dependent options
        self.cb_auto_supplement.toggled.connect(self.cb_preserve_existing.setEnabled)
        self.cb_auto_supplement.toggled.connect(self.cb_set_original_tag.setEnabled)
        self.cb_auto_supplement.toggled.connect(self.cb_enable_original_cover_art.setEnabled)
        self.cb_auto_supplement.toggled.connect(self.cb_show_context_menu.setEnabled)

        layout.addStretch()

    def load(self):
        """Load settings from plugin configuration into UI widgets."""
        if not hasattr(self, 'api') or not self.api:
            return

        cfg = self.api.plugin_config
        auto_supplement = get_config_value(cfg, OPT_AUTO_SUPPLEMENT, True)
        self.cb_auto_supplement.setChecked(auto_supplement)
        self.cb_preserve_existing.setChecked(get_config_value(cfg, OPT_PRESERVE_EXISTING_TAGS, False))
        self.cb_set_original_tag.setChecked(get_config_value(cfg, OPT_SET_ORIGINAL_RELEASE_ID, True))
        self.cb_enable_original_cover_art.setChecked(get_config_value(cfg, OPT_ENABLE_ORIGINAL_COVER_ART, True))
        self.cb_show_context_menu.setChecked(get_config_value(cfg, OPT_SHOW_CONTEXT_MENU, True))

        # Ensure dependent options reflect master toggle enabled state
        self.cb_preserve_existing.setEnabled(auto_supplement)
        self.cb_set_original_tag.setEnabled(auto_supplement)
        self.cb_enable_original_cover_art.setEnabled(auto_supplement)
        self.cb_show_context_menu.setEnabled(auto_supplement)

    def save(self):
        """Save settings from UI widgets into plugin configuration."""
        if not hasattr(self, 'api') or not self.api:
            return

        cfg = self.api.plugin_config
        cfg[OPT_AUTO_SUPPLEMENT] = self.cb_auto_supplement.isChecked()
        cfg[OPT_PRESERVE_EXISTING_TAGS] = self.cb_preserve_existing.isChecked()
        cfg[OPT_SET_ORIGINAL_RELEASE_ID] = self.cb_set_original_tag.isChecked()
        cfg[OPT_ENABLE_ORIGINAL_COVER_ART] = self.cb_enable_original_cover_art.isChecked()
        cfg[OPT_SHOW_CONTEXT_MENU] = self.cb_show_context_menu.isChecked()
