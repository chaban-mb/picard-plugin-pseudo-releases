"""Mock Picard classes for isolated unit testing when Picard core is unavailable."""

from types import SimpleNamespace
from typing import Any
import unittest.mock
from unittest.mock import MagicMock
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


from enum import Enum


class QueueState(Enum):
    _STARTED = 0
    FINISHED = 1
    WAIT = 2


class MockMetadata(dict):
    """Mock Picard Metadata object matching internal Picard behavior."""

    def __init__(self, initial: dict[str, Any] | None = None) -> None:
        super().__init__()
        self._data: dict[str, list[str]] = {}
        if initial:
            for k, v in initial.items():
                self[k] = v

    def __setitem__(self, key: str, value: Any) -> None:
        if isinstance(value, list):
            vals = [str(x) for x in value]
        else:
            vals = [str(value)]
        self._data[key] = vals
        super().__setitem__(key, "; ".join(vals))

    def __getitem__(self, key: str) -> str:
        if key in self._data and self._data[key]:
            return "; ".join(self._data[key])
        return ""

    def __contains__(self, key: object) -> bool:
        return key in self._data

    def __iter__(self):
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __delitem__(self, key: str) -> None:
        self._data.pop(key, None)
        if super().__contains__(key):
            super().__delitem__(key)

    def keys(self):
        return self._data.keys()

    def values(self):
        return [self[k] for k in self._data.keys()]

    def items(self):
        return [(k, self[k]) for k in self._data.keys()]

    def get(self, key: str, default: Any = "") -> Any:
        val = self[key]
        return val if val else default

    def getall(self, key: str) -> list[str]:
        return list(self._data.get(key, []))

    def rawitems(self):
        return ((key, list(values)) for key, values in self._data.items())

    def add_unique(self, key: str, value: Any) -> None:
        value_str = str(value)
        if value_str not in self._data.get(key, []):
            self._data.setdefault(key, []).append(value_str)
            super().__setitem__(key, "; ".join(self._data[key]))

    def copy(self, other: Any = None) -> Any:
        if other is not None:
            self._data = {k: list(v) for k, v in other._data.items()}
            self.clear()
            for k, v in self._data.items():
                super().__setitem__(k, "; ".join(v))
            return self
        cp = MockMetadata()
        cp.copy(self)
        return cp


Metadata = MockMetadata


class MockTrack:
    def __init__(self, title: str = "Test Track", recording_id: str = "rec-123") -> None:
        self.metadata = MockMetadata({"title": title, "musicbrainz_recordingid": recording_id})


Track = MockTrack


class MockAlbum:
    def __init__(
        self,
        album_id: str = "album-123",
        title: str = "",
        artist: str = "",
        status: str = "Official",
    ) -> None:
        self.id = album_id
        self.metadata = MockMetadata(
            {
                "album": title,
                "albumartist": artist,
                "releasestatus": status.lower(),
                "musicbrainz_albumid": album_id,
            }
        )
        self.tracks: list[Any] = []
        self._finalized = False
        self.loaded = False
        self.load_calls: list[dict[str, Any]] = []
        self._pseudo_original_candidates: list[dict[str, Any]] = []
        self._pending_tasks: dict[str, Any] = {}
        self._critical_tasks: set[str] = set()
        self._folksonomy_tags: dict[str, int] = {}
        self._genres: dict[str, int] = {}
        self.per_medium_metadata: dict[int, MockMetadata] = {}
        self.tagger = MagicMock()
        self._release_node: dict[str, Any] | None = None

    def _finalize_loading(self, error: Any = None) -> None:
        self._finalized = True
        self.loaded = True

    def has_critical_tasks(self) -> bool:
        return bool(self._critical_tasks)

    def load(self, **kwargs: Any) -> None:
        self.load_calls.append(kwargs)

    def iterfiles(self) -> Any:
        return iter([])

    def add_task(self, task_id: str, *args: Any, **kwargs: Any) -> None:
        self._pending_tasks[task_id] = kwargs

    def complete_task(self, task_id: str) -> None:
        self._pending_tasks.pop(task_id, None)

    def add_folksonomy_tag(self, name: str, count: int = 1) -> None:
        self._folksonomy_tags[name] = self._folksonomy_tags.get(name, 0) + count

    def add_genre(self, name: str, count: int = 1) -> None:
        self._genres[name] = self._genres.get(name, 0) + count


Album = MockAlbum


class MockCoverArt:
    def __init__(
        self,
        album: Any = None,
        metadata: Any = None,
        release: Any = None,
        front_image_found: bool = False,
    ) -> None:
        self.album = album
        self.metadata = metadata if metadata is not None else MockMetadata({
            "musicbrainz_albumid": "pseudo-release-uuid-9fe",
            "releasestatus": "pseudo-release",
        })
        self.release = release if release is not None else {
            "id": "pseudo-release-uuid-9fe",
            "cover-art-archive": {"artwork": True},
        }
        self.front_image_found = front_image_found


class MockFile:
    def __init__(self, metadata: dict[str, Any] | None = None) -> None:
        self.metadata = MockMetadata(metadata or {})
        self.orig_metadata = self.metadata.copy()


class MockPluginConfig(dict):
    def register_option(self, name: str, default: Any, **kwargs: Any) -> None:
        if name not in self:
            self[name] = default


class MockPluginApi:
    def __init__(self, initial_config: dict[str, Any] | None = None) -> None:
        defaults = {}
        if initial_config:
            defaults.update(initial_config)
        self.plugin_config = MockPluginConfig(defaults)
        self.global_config = SimpleNamespace(
            setting={
                'preferred_release_countries': [],
                'release_ars': False,
                'use_genres': False,
                'only_my_genres': False,
            }
        )
        self.tagger = SimpleNamespace(
            window=SimpleNamespace(selected_objects=[]),
            config=self.plugin_config,
        )
        self.processors: list[Any] = []
        self.providers: list[Any] = []
        self.album_actions: list[Any] = []
        self.options_pages: list[Any] = []
        self.removal_processors: list[Any] = []
        self.script_variables: list[tuple[str, str, str]] = []
        self.added_tasks: list[Any] = []
        self.completed_tasks: list[Any] = []
        self.logger = MagicMock()
        self.mb_api = MagicMock()

    def tr(self, key: str, text: str | None = None, **kwargs: Any) -> str:
        return text or key

    def trn(self, singular: str, plural: str, n: int = 1, **kwargs: Any) -> str:
        return singular if n == 1 else plural

    def register_album_metadata_processor(self, func: Any, priority: int = 50) -> None:
        self.processors.append((func, priority))

    def register_album_post_removal_processor(self, func: Any) -> None:
        self.removal_processors.append(func)

    def register_album_action(self, action_cls: Any) -> None:
        action_cls.api = self
        self.album_actions.append(action_cls)

    def register_cover_art_provider(self, provider_cls: Any) -> None:
        provider_cls.api = self
        self.providers.append(provider_cls)

    def register_options_page(self, page_cls: Any) -> None:
        page_cls.api = self
        self.options_pages.append(page_cls)

    def register_script_variable(self, name: str, documentation: str = "", title: str = "", **kwargs: Any) -> None:
        self.script_variables.append((name, documentation, title))

    def add_album_task(
        self,
        album: Any,
        task_id: str,
        description: str,
        timeout: float | None = None,
        request_factory: Any = None,
        blocking: bool = False,
    ) -> None:
        self.added_tasks.append((album, task_id, blocking))
        meta = getattr(album, 'metadata', None)
        if meta and hasattr(meta, 'get'):
            self.metadata_at_task_add = meta.get('~original_musicbrainz_albumid', '')
        else:
            self.metadata_at_task_add = ''
        if hasattr(album, '_pending_tasks'):
            album._pending_tasks[task_id] = description
        if blocking and hasattr(album, '_critical_tasks'):
            album._critical_tasks.add(task_id)
        if request_factory:
            request_factory()

    def complete_album_task(self, album: Any, task_id: str) -> None:
        self.completed_tasks.append((album, task_id))
        if hasattr(album, '_pending_tasks'):
            album._pending_tasks.pop(task_id, None)
        was_critical = task_id in getattr(album, '_critical_tasks', set())
        if hasattr(album, '_critical_tasks'):
            album._critical_tasks.discard(task_id)
        finalize_loading = getattr(album, '_finalize_loading', None)
        if (
            was_critical
            and hasattr(album, 'has_critical_tasks')
            and not album.has_critical_tasks()
            and not getattr(album, 'loaded', False)
            and callable(finalize_loading)
        ):
            finalize_loading(None)


PluginApi = MockPluginApi


class CoverArtProviderCaa:
    NAME = "Cover Art Archive"
    TITLE = "Cover Art Archive: Release"
    OPTIONS = None
    QueueState = QueueState

    def __init__(self, coverart: Any = None) -> None:
        self.coverart = coverart
        self.metadata: dict[str, Any] = getattr(coverart, "metadata", {}) if coverart else {}
        self.release: dict[str, Any] = getattr(coverart, "release", {}) if coverart else {}
        self.album = getattr(coverart, "album", None) if coverart else None

    def enabled(self) -> bool:
        return not (self.coverart and getattr(self.coverart, "front_image_found", False))

    def queue_images(self) -> Any:
        album = getattr(self, "album", None)
        album_id = self.metadata.get("musicbrainz_albumid", "")
        task_id = f"caa_json_{album_id}"
        if album and hasattr(album, "add_task"):
            album.add_task(task_id, description=f"CAA JSON metadata for {album_id}")
        return self.QueueState.WAIT

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
