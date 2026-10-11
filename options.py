"""Options page for user configuration of pseudo-release features."""

from typing import (
    ClassVar,
)

from PyQt6 import (
    QtCore,
    QtWidgets,
)
from picard.plugin3.api import (
    OptionsPage,
    PageOptionConfigs,
    t_,
)


class PseudoReleaseOptionsPage(OptionsPage):
    """Picard Options page for configuring Pseudo-Release features."""

    NAME = "pseudo_releases"
    TITLE = t_("options.title", "Pseudo-Releases")
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
            "MusicBrainz [pseudo-releases](https://musicbrainz.org/doc/Style/Specific_types_of_releases/Pseudo-Releases) "
            "contain alternate tracklists (such as transliterated or translated titles) linked to an original release "
            "via the [transl-tracklisting](https://musicbrainz.org/relationship/fc399d47-23a7-4c28-bfcf-0607a562b644) "
            "relationship.\n\n"
            "When a pseudo-release is loaded, this plugin automatically supplements missing metadata "
            "(`date`, `releasecountry`, `barcode`, `media`, `label`, and `catalognumber`) from the best-matched original release.\n\n"
            "Additionally, the original release ID is made available to tagger scripts and file naming scripts "
            "via the hidden variable `%_original_musicbrainz_albumid%`.",
        )
        self.lbl_info = QtWidgets.QLabel(info_text, self)
        self.lbl_info.setTextFormat(QtCore.Qt.TextFormat.MarkdownText)
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
                "Pseudo-releases are not supposed to have cover art in MusicBrainz. Artwork is fetched from the "
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
                "Provider order and enablement are configured under **Options > Cover Art > Providers**.",
            ),
            self.group_cover_art,
        )
        self.lbl_cover_art_note.setTextFormat(QtCore.Qt.TextFormat.MarkdownText)
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

    def _open_cover_providers_page(self, checked: bool = False):
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
