"""Lightweight Picard test doubles wrapping real Picard runtime types."""

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from picard.metadata import Metadata
from picard.options import StandardizeArtistNames


MockMetadata = Metadata


class MockTrack:
    def __init__(self, title: str = "Test Track", recording_id: str = "rec-123") -> None:
        self.metadata = Metadata({"title": title, "musicbrainz_recordingid": recording_id})


class MockAlbum:
    def __init__(
        self,
        album_id: str = "album-123",
        title: str = "",
        artist: str = "",
        status: str = "Official",
        release_node: dict[str, Any] | None = None,
    ) -> None:
        self.id = album_id
        self.metadata = Metadata(
            {
                "album": title,
                "albumartist": artist,
                "releasestatus": status.lower(),
                "musicbrainz_albumid": album_id,
            }
        )
        self._new_metadata: Metadata | None = None
        self.tracks: list[Any] = []
        self._finalized = False
        self.loaded = False
        self.load_calls: list[dict[str, Any]] = []
        self._pseudo_original_candidates: list[dict[str, Any]] = []
        self._pending_tasks: dict[str, Any] = {}
        self._critical_tasks: set[str] = set()
        self._folksonomy_tags: dict[str, int] = {}
        self._genres: dict[str, int] = {}
        self.per_medium_metadata: dict[int, Metadata] = {}
        self.tagger = MagicMock()
        self._release_node: dict[str, Any] | None = release_node

    def _finalize_loading(self, error: Any = None) -> None:
        if self.has_critical_tasks():
            return
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
        request_factory = kwargs.get("request_factory")
        if request_factory:
            request_factory()

    def complete_task(self, task_id: str) -> None:
        self._pending_tasks.pop(task_id, None)

    def add_folksonomy_tag(self, name: str, count: int = 1) -> None:
        self._folksonomy_tags[name] = self._folksonomy_tags.get(name, 0) + count

    def add_genre(self, name: str, count: int = 1) -> None:
        self._genres[name] = self._genres.get(name, 0) + count


class MockCoverArt:
    def __init__(
        self,
        album: Any = None,
        metadata: Any = None,
        release: Any = None,
        front_image_found: bool = False,
    ) -> None:
        self.album = album
        self.metadata = (
            metadata
            if metadata is not None
            else Metadata(
                {
                    "musicbrainz_albumid": "pseudo-release-uuid-9fe",
                    "releasestatus": "pseudo-release",
                }
            )
        )
        self.release = (
            release
            if release is not None
            else {
                "id": "pseudo-release-uuid-9fe",
                "cover-art-archive": {"artwork": True},
            }
        )
        self.front_image_found = front_image_found


class MockFile:
    def __init__(self, metadata: dict[str, Any] | None = None) -> None:
        self.metadata = Metadata(metadata or {})
        self.orig_metadata = Metadata()
        self.orig_metadata.copy(self.metadata)


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
                "preferred_release_countries": [],
                "release_ars": False,
                "use_genres": False,
                "only_my_genres": False,
                "standardize_artist_names": StandardizeArtistNames.NONE,
                "translate_artist_names": False,
                "translate_artist_names_script_exception": False,
                "always_standardize_multivalue_artist": False,
                "standardize_instruments": True,
                "standardize_vocals": True,
                "translation_locales": ["en"],
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

    def register_script_variable(
        self, name: str, documentation: str = "", title: str = "", **kwargs: Any
    ) -> None:
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
        if hasattr(album, "_pending_tasks"):
            album._pending_tasks[task_id] = description
        if blocking and hasattr(album, "_critical_tasks"):
            album._critical_tasks.add(task_id)
        if request_factory:
            request_factory()

    def complete_album_task(self, album: Any, task_id: str) -> None:
        self.completed_tasks.append((album, task_id))
        if hasattr(album, "_pending_tasks"):
            album._pending_tasks.pop(task_id, None)
        if hasattr(album, "_critical_tasks"):
            album._critical_tasks.discard(task_id)
