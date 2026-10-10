"""Pseudo-Releases Picard plugin for catalog and cover-art supplementation."""

from collections.abc import Callable
from typing import Any

try:
    from PyQt6 import QtGui, QtWidgets
    from picard.debug_opts import DebugOpt
    from picard.plugin3.api import (
        Album,
        BaseAction,
        Metadata,
        PluginApi,
        Track,
    )
except ImportError:
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

        def setCheckable(self, value):
            self.checkable = value

        def setChecked(self, value):
            self.checked = value

        def setEnabled(self, enabled):
            self.enabled = bool(enabled)

        def setToolTip(self, text):
            self.tooltip = text

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

        def addAction(self, text):
            action = _FallbackAction(text)
            self.actions.append(action)
            return action

        def addSeparator(self):
            self.actions.append(None)

        def setToolTipsVisible(self, visible):
            self.tooltips_visible = bool(visible)

        def exec(self, *args):
            return self.selected_action

        def deleteLater(self):
            pass

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

    class QtWidgets:  # type: ignore[no-redef]
        QMenu = _FallbackMenu

    # Fallback types for unit testing outside Picard runtime
    class DebugOpt:
        PLUGIN_DEVELOPMENT = "plugin-development"

    class BaseAction:  # type: ignore[no-redef]
        api: Any = None

        def __init__(self, parent=None):
            self.tagger = getattr(self.api, 'tagger', None)
            self._menu = None
            self._enabled = True
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

try:
    from .caa_provider import PseudoReleaseCoverArtProvider
    from .candidates import (
        find_related_releases,
        select_best_original_candidate,
    )
    from .constants import (
        OPT_AUTO_SUPPLEMENT,
        OPT_ENABLE_ORIGINAL_COVER_ART,
        OPT_PRESERVE_EXISTING_TAGS,
        OPT_SET_ORIGINAL_RELEASE_ID,
        OPT_SHOW_CONTEXT_MENU,
        PSEUDO_RELEASE_STATUS,
        TAG_ORIGINAL_RELEASE_ID,
        get_config_value,
    )
    from .metadata_engine import (
        supplement_pseudo_metadata,
    )
    from .options import PseudoReleaseOptionsPage
except (ImportError, ValueError):
    from caa_provider import PseudoReleaseCoverArtProvider
    from candidates import (
        find_related_releases,
        select_best_original_candidate,
    )
    from constants import (
        OPT_AUTO_SUPPLEMENT,
        OPT_ENABLE_ORIGINAL_COVER_ART,
        OPT_PRESERVE_EXISTING_TAGS,
        OPT_SET_ORIGINAL_RELEASE_ID,
        OPT_SHOW_CONTEXT_MENU,
        PSEUDO_RELEASE_STATUS,
        TAG_ORIGINAL_RELEASE_ID,
        get_config_value,
    )
    from metadata_engine import (
        supplement_pseudo_metadata,
    )
    from options import PseudoReleaseOptionsPage


class ManifestTranslations:
    """Translation strings for the plugin manifest."""

    NAME = "Pseudo-Releases"
    DESC = (
        "Supplements pseudo-releases with original catalog metadata and cover art."
    )


class ChooseLinkedOriginalAction(BaseAction):
    """Choose which linked original release supplies catalog metadata."""

    TITLE = "Linked original editions"

    def __init__(self, parent=None):
        super().__init__(parent)
        cfg = None
        if hasattr(self, 'tagger'):
            cfg = getattr(self.tagger, 'config', None)
        if not cfg and getattr(PseudoReleasePlugin, 'api', None):
            cfg = getattr(PseudoReleasePlugin.api, 'plugin_config', None)
        if cfg:
            if not get_config_value(cfg, OPT_AUTO_SUPPLEMENT, True) or not get_config_value(
                cfg, OPT_SHOW_CONTEXT_MENU, True
            ):
                self.setEnabled(False)
                if hasattr(self, 'setVisible'):
                    self.setVisible(False)
                return

        window = getattr(self.tagger, 'window', None)
        albums = getattr(window, 'selected_objects', [])
        if len(albums) != 1:
            self.setEnabled(False)
            return

        album = albums[0]
        if album.metadata.get('releasestatus') != 'pseudo-release':
            self.setEnabled(False)
            return

        candidates = getattr(album, '_pseudo_original_candidates', [])
        if not candidates:
            self.setEnabled(False)
            return

        menu = QtWidgets.QMenu(window)
        menu.setToolTipsVisible(True)
        self.destroyed.connect(lambda *_: menu.deleteLater())
        self.setMenu(menu)
        selection_group = QtGui.QActionGroup(menu)
        selection_group.setExclusive(True)

        heading = menu.addAction("Tracks / Year / Country / Format / Label / Cat No")
        heading_font = heading.font()
        heading_font.setBold(True)
        heading_font.setUnderline(False)
        heading.setFont(heading_font)
        heading.setEnabled(False)

        current_id = album.metadata.get(TAG_ORIGINAL_RELEASE_ID)
        if (
            not current_id
            and getattr(album, '_pseudo_original_selection_mode', 'automatic') == 'manual'
        ):
            current_id = getattr(album, '_pseudo_original_release_choice', None)
        detail_cache = getattr(album, '_pseudo_original_details', {})
        for candidate in candidates:
            release_id = candidate.get('id')
            if not release_id:
                continue
            details = detail_cache.get(release_id, candidate)
            label = PseudoReleasePlugin._format_original_candidate(details).replace('&', '&&')
            action = menu.addAction(label)
            tooltip = PseudoReleasePlugin._format_original_candidate_tooltip(details)
            if tooltip:
                action.setToolTip(tooltip)
            action.setCheckable(True)
            action.setChecked(release_id == current_id)
            selection_group.addAction(action)
            action.triggered.connect(
                lambda checked=False, selected_id=release_id: PseudoReleasePlugin.select_linked_original(
                    album,
                    selected_id,
                )
            )

    def callback(self, objs) -> None:
        pass


class PseudoReleasePlugin:
    """Plugin logic orchestrator for MusicBrainz Pseudo-Releases."""

    in_flight_albums: set[str] = set()
    api: PluginApi | None = None

    @classmethod
    def _log_debug(cls, api: PluginApi, message: str, *args: Any) -> None:
        """Helper to log via debug_if when available."""
        logger = getattr(api, 'logger', None)
        if not logger:
            return
        if hasattr(logger, 'debug_if'):
            logger.debug_if(DebugOpt.PLUGIN_DEVELOPMENT, message, *args)
        else:
            logger.debug(message, *args)

    @classmethod
    def remove_album(cls, api: PluginApi, album: Album) -> None:
        """Clean up per-album state when an album is removed from Picard."""
        album_id = getattr(album, 'id', None)
        if album_id and album_id in cls.in_flight_albums:
            cls.in_flight_albums.discard(album_id)
            cls._log_debug(api, "Cleaned up in-flight state for album %s", album_id)

    @classmethod
    def process_album_metadata(
        cls,
        api: PluginApi,
        album: Album,
        album_metadata: Metadata,
        release_node: dict[str, Any],
    ) -> None:
        """Supplement loaded pseudo-releases with data from linked original releases."""
        album_id = getattr(album, 'id', '')
        if album_id in cls.in_flight_albums:
            return

        if release_node.get('status') != PSEUDO_RELEASE_STATUS:
            return

        source_id = release_node.get('id')
        if getattr(album, '_pseudo_original_source_id', None) != source_id:
            album._pseudo_original_release_choice = None
            album._pseudo_original_selection_mode = 'automatic'
            album._pseudo_original_source_id = source_id

        candidates = find_related_releases(release_node, direction='backward')
        album._pseudo_original_candidates = candidates

        selection_mode = getattr(album, '_pseudo_original_selection_mode', 'automatic')
        if selection_mode == 'manual':
            preferred_id = getattr(album, '_pseudo_original_release_choice', None)
        else:
            already_enriched_id = album_metadata.get(TAG_ORIGINAL_RELEASE_ID)
            if already_enriched_id:
                preferred_id = already_enriched_id
            elif get_config_value(api.plugin_config, OPT_AUTO_SUPPLEMENT, True):
                files = getattr(album, 'iterfiles', lambda: [])() if hasattr(album, 'iterfiles') else []
                preferred = select_best_original_candidate(
                    candidates=candidates,
                    album_metadata=album_metadata,
                    files=list(files),
                    disc_ids=getattr(album, 'discids', None),
                )
                preferred_id = preferred.get('id') if preferred else None
            else:
                preferred_id = None

        cls._prefetch_linked_original_details(api, album, candidates, preferred_id)

        already_enriched_id = album_metadata.get(TAG_ORIGINAL_RELEASE_ID)
        # Avoid re-processing already enriched albums after preserving chooser state.
        if already_enriched_id and selection_mode != 'manual':
            return
        if (
            selection_mode != 'manual'
            and not get_config_value(api.plugin_config, OPT_AUTO_SUPPLEMENT, True)
        ):
            return

        cls._handle_supplement_pseudo(api, album, album_metadata, preferred_id, candidates)

    @classmethod
    def _handle_supplement_pseudo(
        cls,
        api: PluginApi,
        album: Album,
        album_metadata: Metadata,
        preferred_id: str | None,
        candidates: list[dict[str, Any]],
    ) -> None:
        """Direction 1: Find best matching original release and queue supplementation."""
        if not candidates:
            cls._log_debug(api, "No backward transl-tracklisting relations found for %s", album.id)
            return

        best_original = next(
            (candidate for candidate in candidates if candidate.get('id') == preferred_id),
            None,
        )

        if not best_original or not best_original.get('id'):
            return

        orig_id = best_original['id']
        cls._log_debug(api, "Selected original candidate %s for pseudo-release %s", orig_id, album.id)
        album._pseudo_original_id = orig_id
        if get_config_value(api.plugin_config, OPT_SET_ORIGINAL_RELEASE_ID, True):
            album_metadata[TAG_ORIGINAL_RELEASE_ID] = orig_id

        cached_release = getattr(album, '_pseudo_original_details', {}).get(orig_id)
        if cached_release:
            preserve_existing = get_config_value(api.plugin_config, OPT_PRESERVE_EXISTING_TAGS, False)
            set_original_id = get_config_value(api.plugin_config, OPT_SET_ORIGINAL_RELEASE_ID, True)
            supplement_pseudo_metadata(
                album_metadata,
                cached_release,
                preserve_existing=preserve_existing,
                set_original_id=set_original_id,
            )
            cls._log_debug(api, "Supplemented pseudo-release %s from cached original %s", album.id, orig_id)
            return
        cls._queue_enrichment(api, album, orig_id)

    @classmethod
    def _prefetch_linked_original_details(
        cls,
        api: PluginApi,
        album: Album,
        candidates: list[dict[str, Any]],
        preferred_id: str | None,
    ) -> None:
        """Fetch menu details during album processing, never while opening the menu."""
        if not hasattr(api, 'mb_api'):
            return

        detail_cache = getattr(album, '_pseudo_original_details', None)
        if detail_cache is None:
            detail_cache = {}
            album._pseudo_original_details = detail_cache
        loading_ids = getattr(album, '_pseudo_original_details_loading_ids', None)
        if loading_ids is None:
            loading_ids = set()
            album._pseudo_original_details_loading_ids = loading_ids

        for fallback in candidates:
            release_id = fallback.get('id')
            if not release_id or release_id == preferred_id:
                continue
            if release_id in detail_cache or release_id in loading_ids:
                continue

            loading_ids.add(release_id)

            def on_loaded(
                document: dict[str, Any],
                http: Any,
                error: Any,
                fallback: dict[str, Any] = fallback,
            ) -> None:
                loading_ids.discard(fallback['id'])
                if not error and document:
                    detail_cache[fallback['id']] = document

            api.mb_api.get_release_by_id(
                release_id,
                on_loaded,
                inc=['labels', 'media', 'discids'],
            )

    @staticmethod
    def _format_original_candidate(candidate: dict[str, Any]) -> str:
        """Format a compact edition label for the linked-original menu."""
        media = candidate.get('media') or []
        track_counts = [
            str(medium.get('track-count') or len(medium.get('tracks', [])))
            for medium in media
        ]
        tracks = '+'.join(count for count in track_counts if count != '0')
        year = (candidate.get('date') or '')[:4]
        country = candidate.get('country') or '??'

        format_counts: dict[str, int] = {}
        for medium in media:
            format_name = medium.get('format') or '(unknown)'
            format_counts[format_name] = format_counts.get(format_name, 0) + 1
        formats = ', '.join(
            f"{count}\u00d7{format_name}"
            for format_name, count in format_counts.items()
        )

        labels = []
        catalog_numbers = []
        for label_info in candidate.get('label-info', []):
            label_name = (label_info.get('label') or {}).get('name')
            catalog_number = label_info.get('catalog-number')
            if label_name and label_name not in labels:
                labels.append(label_name)
            if catalog_number:
                catalog_numbers.append(catalog_number)

        return ' / '.join((
            tracks,
            year,
            country,
            formats,
            ', '.join(labels),
            ', '.join(catalog_numbers),
        ))

    @staticmethod
    def _format_original_candidate_tooltip(candidate: dict[str, Any]) -> str:
        """Format additional release details using Picard's Other versions fields."""
        details = [
            f"Packaging: {candidate.get('packaging') or '??'}",
            f"Barcode: {candidate.get('barcode') or '[no barcode]'}",
        ]
        disambiguation = candidate.get('disambiguation')
        if disambiguation:
            details.append(f"Disambiguation: {disambiguation}")
        return '\n'.join(details)

    @staticmethod
    def select_linked_original(album: Album, selected_id: str) -> None:
        """Set the manually selected edition and reload the album."""
        current_id = album.metadata.get(TAG_ORIGINAL_RELEASE_ID)
        album._pseudo_original_selection_mode = 'manual'
        album._pseudo_original_release_choice = selected_id
        if selected_id == current_id:
            return

        album.load(priority=True, refresh=True)

    @classmethod
    def _queue_enrichment(
        cls,
        api: PluginApi,
        album: Album,
        target_mbid: str,
    ) -> None:
        """Fetch the original release asynchronously to supplement pseudo-release metadata."""
        album_id = getattr(album, 'id', '')
        cls.in_flight_albums.add(album_id)

        task_id = f"pseudo_enrich_{target_mbid}"
        inc = [
            'artists',
            'labels',
            'recordings',
            'release-rels',
            'artist-credits',
            'media',
            'discids',
        ]

        def on_loaded(document: dict[str, Any], http: Any, error: Any) -> None:
            try:
                if error:
                    api.logger.error("Failed to load release %s: %s", target_mbid, error)
                    return

                album._pseudo_original_details = getattr(album, '_pseudo_original_details', {})
                album._pseudo_original_details[target_mbid] = document
                preserve_existing = get_config_value(api.plugin_config, OPT_PRESERVE_EXISTING_TAGS, False)
                set_original_id = get_config_value(api.plugin_config, OPT_SET_ORIGINAL_RELEASE_ID, True)
                supplement_pseudo_metadata(
                    album.metadata,
                    document,
                    preserve_existing=preserve_existing,
                    set_original_id=set_original_id,
                )
                new_meta = getattr(album, '_new_metadata', None)
                if new_meta is not None:
                    supplement_pseudo_metadata(
                        new_meta,
                        document,
                        preserve_existing=preserve_existing,
                        set_original_id=set_original_id,
                    )
                cls._log_debug(api, "Supplemented pseudo-release %s with original %s", album_id, target_mbid)

            except Exception as exc:
                api.logger.error("Error processing pseudo-release enrichment: %s", exc)

            finally:
                cls.in_flight_albums.discard(album_id)
                if hasattr(api, 'complete_album_task'):
                    api.complete_album_task(album, task_id)
                if hasattr(album, '_finalize_loading'):
                    album._finalize_loading(None)
                if not error:
                    cls._trigger_cover_art_retrieval(album, api)

        if hasattr(api, 'add_album_task') and hasattr(api, 'mb_api'):
            api.add_album_task(
                album=album,
                task_id=task_id,
                description=f"Loading pseudo-release data for {target_mbid}",
                timeout=15.0,
                request_factory=lambda: api.mb_api.get_release_by_id(target_mbid, on_loaded, inc=inc),
                blocking=True,
            )

    @classmethod
    def _trigger_cover_art_retrieval(cls, album: Album, api: PluginApi | None = None) -> None:
        """Trigger cover art retrieval for the album after enrichment if needed."""
        if api and not get_config_value(api.plugin_config, OPT_ENABLE_ORIGINAL_COVER_ART, True):
            return
        try:
            from picard.coverart import _retrieve_coverart
            release_node = getattr(album, '_release_node_cache', getattr(album, '_release_node', {}))
            _retrieve_coverart(album, album.metadata, release_node)
        except Exception:
            pass

def enable(api: PluginApi) -> None:
    """Called when the plugin is enabled in Picard."""
    PseudoReleasePlugin.api = api

    # Register default plugin configurations
    api.plugin_config.register_option(OPT_AUTO_SUPPLEMENT, True)
    api.plugin_config.register_option(OPT_PRESERVE_EXISTING_TAGS, False)
    api.plugin_config.register_option(OPT_SET_ORIGINAL_RELEASE_ID, True)
    api.plugin_config.register_option(OPT_ENABLE_ORIGINAL_COVER_ART, True)
    api.plugin_config.register_option(OPT_SHOW_CONTEXT_MENU, True)

    plugin = PseudoReleasePlugin

    # Register album metadata processor
    api.register_album_metadata_processor(plugin.process_album_metadata, priority=50)

    # Register a manual chooser for linked original editions
    if hasattr(api, 'register_album_action'):
        api.register_album_action(ChooseLinkedOriginalAction)

    # Register post-removal processor for cleanup
    if hasattr(api, 'register_album_post_removal_processor'):
        api.register_album_post_removal_processor(plugin.remove_album)

    # Register Cover Art Archive provider
    api.register_cover_art_provider(PseudoReleaseCoverArtProvider)

    # Register Options page
    api.register_options_page(PseudoReleaseOptionsPage)


def disable(api: PluginApi | None = None) -> None:
    """Called when the plugin is disabled in Picard."""
    PseudoReleasePlugin.in_flight_albums.clear()
    PseudoReleasePlugin.api = None
