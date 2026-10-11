"""Mock Picard classes for isolated unit testing when Picard core is unavailable."""

from typing import Any
import webbrowser

try:
    from PyQt6 import QtCore, QtWidgets

    _BaseWidget = QtWidgets.QWidget
    _BaseObject = QtCore.QObject
except ImportError:
    from tests.mocks.mock_qt import (
        MockQtCore,
        _DummyWidget,
    )

    _BaseWidget = _DummyWidget
    _BaseObject = MockQtCore.QObject
from tests.mocks.mock_qt import (
    _DummySignal,
    _DummyWidget,
)


class DebugOpt:
    PLUGIN_DEVELOPMENT = "plugin-development"


def t_(key: str, text: str | None = None, plural: str | None = None) -> str | tuple[str, str, str]:
    if plural is not None:
        return (key, str(text or ""), plural)
    return key


class BaseAction(_BaseObject):
    api: Any = None

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.tagger = getattr(self.api, "tagger", None)
        self._menu: Any = None
        self._enabled = True
        self.destroyed = _DummySignal()

    def setMenu(self, menu: Any) -> None:
        self._menu = menu

    def menu(self) -> Any:
        return self._menu

    def setEnabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)

    def isEnabled(self) -> bool:
        return self._enabled

    def callback(self, objs: Any) -> None:
        pass


class OptionsPage(_BaseWidget):
    NAME = ""
    TITLE = ""
    PARENT = None
    api: Any = None
    OPTIONS: dict[str, Any] = {}


PageOptionConfigs = dict[str, Any]


class PluginApi:
    pass


class Album:
    def __init__(self, album_id: str = "album-123", title: str = "", status: str = "Official") -> None:
        self.id = album_id
        self.metadata: Any = None
        self.tracks: list[Any] = []
        self._finalized = False

    def iterfiles(self):
        return iter([])

    def _finalize_loading(self, error: Any = None) -> None:
        self._finalized = True



class Track:
    pass


class Metadata:
    pass


class CoverArtProviderCaa:
    NAME = "Cover Art Archive"
    TITLE = "Cover Art Archive: Release"
    OPTIONS = None

    def __init__(self, coverart: Any = None) -> None:
        self.coverart = coverart
        self.metadata: dict[str, Any] = getattr(coverart, "metadata", {}) if coverart else {}
        self.release: dict[str, Any] = getattr(coverart, "release", {}) if coverart else {}
        self.album = getattr(coverart, "album", None) if coverart else None

    def enabled(self) -> bool:
        return not (self.coverart and getattr(self.coverart, "front_image_found", False))

    @property
    def _caa_path(self) -> str:
        return f"/release/{self.metadata.get('musicbrainz_albumid', '')}/"

    @property
    def _has_suitable_artwork(self) -> bool:
        caa = self.release.get("cover-art-archive", {})
        return bool(caa.get("artwork"))

    @classmethod
    def display_title(cls) -> str:
        title = getattr(cls, "TITLE", getattr(cls, "NAME", None)) or cls.__name__
        api = getattr(cls, "api", None)
        if api and hasattr(api, "tr"):
            if isinstance(title, tuple) and hasattr(api, "trn"):
                return api.trn(*title, n=1)
            return api.tr(title)
        return title[1] if isinstance(title, tuple) else title


def add_genres_from_node(node: dict[str, Any], obj: Any) -> None:
    if obj is None or not isinstance(node, dict):
        return
    tags = node.get("tags")
    if isinstance(tags, list):
        for tag in tags:
            if hasattr(obj, "add_folksonomy_tag") and isinstance(tag, dict):
                obj.add_folksonomy_tag(tag.get("name"), tag.get("count", 1))
    genres = node.get("genres")
    if isinstance(genres, list):
        for genre in genres:
            if hasattr(obj, "add_genre") and isinstance(genre, dict):
                obj.add_genre(genre.get("name"), genre.get("count", 1))


# Fallbacks for Picard utilities
def countries_from_node(node: dict[str, Any]) -> list[str]:
    countries: list[str] = []
    events = node.get("release-events") if isinstance(node, dict) else None
    for event in events if isinstance(events, list) else []:
        try:
            code = event["area"]["iso-3166-1-codes"][0]
            if code:
                countries.append(code)
        except (KeyError, IndexError, TypeError):
            pass
    return sorted(countries)


def countries_shortlist(countries: list[str]) -> str:
    if not countries or not isinstance(countries, list):
        return ""
    str_countries = [str(c) for c in countries if c]
    if not str_countries:
        return ""
    if len(str_countries) <= 6:
        return "+".join(str_countries)
    return f"{'+'.join(str_countries[:3])}+…+{'+'.join(str_countries[-3:])}"


def label_info_from_node(node: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    labels: list[str] = []
    catalog_numbers: list[str] = []
    if not isinstance(node, list):
        return (labels, catalog_numbers)
    for label_info in node:
        if isinstance(label_info, dict):
            label_obj = label_info.get("label")
            label_name = label_obj.get("name") if isinstance(label_obj, dict) else None
            catalog_number = label_info.get("catalog-number")
            if label_name:
                lbl_str = str(label_name)
                if lbl_str not in labels:
                    labels.append(lbl_str)
            if catalog_number:
                cat_str = str(catalog_number)
                if cat_str not in catalog_numbers:
                    catalog_numbers.append(cat_str)
    return (labels, catalog_numbers)


def media_formats_from_node(node: list[dict[str, Any]]) -> str:
    if not isinstance(node, list):
        return ""
    formats_count: dict[str, int] = {}
    formats_order: list[str] = []
    for medium in node:
        if not isinstance(medium, dict):
            continue
        fmt = medium.get("format")
        text = str(fmt) if fmt else "(unknown)"
        if text in formats_count:
            formats_count[text] += 1
        else:
            formats_count[text] = 1
            formats_order.append(text)
    formats: list[str] = []
    for medium_format in formats_order:
        count = formats_count[medium_format]
        if count > 1:
            formats.append(f"{count}×{medium_format}")
        else:
            formats.append(medium_format)
    return " + ".join(formats)


def pgettext_attributes(context: str, message: str) -> str:
    return message


def _(text: str) -> str:
    return text


VERSIONS_MAX_TRACKS = 10
VERSIONS_EXTRA_HEADINGS = {
    "packaging": "Packaging",
    "barcode": "Barcode",
    "disambiguation": "Disambiguation",
}

webbrowser2 = webbrowser
