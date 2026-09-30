"""Pseudo-Releases Picard plugin for catalog and cover-art supplementation."""

from collections.abc import Callable
from typing import Any

try:
    from PyQt6 import QtWidgets
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
    class _FallbackInputDialog:
        @staticmethod
        def getItem(*args, **kwargs):
            return "", False

    class QtWidgets:  # type: ignore[no-redef]
        QInputDialog = _FallbackInputDialog

    # Fallback types for unit testing outside Picard runtime
    class DebugOpt:
        PLUGIN_DEVELOPMENT = "plugin-development"

    class BaseAction:  # type: ignore[no-redef]
        api: Any = None

    class PluginApi:  # type: ignore[no-redef]
        pass

    class Album:  # type: ignore[no-redef]
        pass

    class Track:  # type: ignore[no-redef]
        pass

    class Metadata:  # type: ignore[no-redef]
        pass

    def t_(key: str, text: str | None = None, plural: str | None = None) -> str:
        return text or key

try:
    from .caa_provider import PseudoReleaseCoverArtProvider
    from .candidates import (
        find_related_releases,
        select_best_original_candidate,
    )
    from .constants import (
        OPT_AUTO_SUPPLEMENT,
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

    TITLE = t_("action.choose_linked_original", "Choose linked original...")

    def callback(self, objs) -> None:
        if len(objs) != 1:
            return
        PseudoReleasePlugin.choose_linked_original(self.api, objs[0])


class PseudoReleasePlugin:
    """Plugin logic orchestrator for MusicBrainz Pseudo-Releases."""

    in_flight_albums: set[str] = set()

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

        # Avoid re-processing already enriched albums after preserving chooser state.
        if album_metadata.get(TAG_ORIGINAL_RELEASE_ID):
            return
        selection_mode = getattr(album, '_pseudo_original_selection_mode', 'automatic')
        if (
            selection_mode != 'manual'
            and not get_config_value(api.plugin_config, OPT_AUTO_SUPPLEMENT, True)
        ):
            return

        cls._handle_supplement_pseudo(api, album, album_metadata, candidates)

    @classmethod
    def _handle_supplement_pseudo(
        cls,
        api: PluginApi,
        album: Album,
        album_metadata: Metadata,
        candidates: list[dict[str, Any]],
    ) -> None:
        """Direction 1: Find best matching original release and queue supplementation."""
        if not candidates:
            cls._log_debug(api, "No backward transl-tracklisting relations found for %s", album.id)
            return

        best_original = None
        if getattr(album, '_pseudo_original_selection_mode', 'automatic') == 'manual':
            chosen_id = getattr(album, '_pseudo_original_release_choice', None)
            best_original = next(
                (candidate for candidate in candidates if candidate.get('id') == chosen_id),
                None,
            )
        files = getattr(album, 'iterfiles', lambda: [])() if hasattr(album, 'iterfiles') else []
        disc_ids = getattr(album, 'discids', None)

        if best_original is None:
            best_original = select_best_original_candidate(
                candidates=candidates,
                album_metadata=album_metadata,
                files=list(files),
                disc_ids=disc_ids,
            )

        if not best_original or not best_original.get('id'):
            return

        orig_id = best_original['id']
        cls._log_debug(api, "Selected original candidate %s for pseudo-release %s", orig_id, album.id)
        cls._queue_enrichment(api, album, orig_id)

    @staticmethod
    def _format_original_candidate(candidate: dict[str, Any], current_id: str | None) -> str:
        """Format an original release's distinguishing details for the chooser."""
        release_id = candidate.get('id', '')
        title = candidate.get('title') or 'Untitled release'
        media = candidate.get('media') or []
        formats = list(dict.fromkeys(medium.get('format') for medium in media if medium.get('format')))
        track_count = sum(medium.get('track-count', 0) for medium in media)
        media_summary = ', '.join(formats) or 'format unknown'
        if media:
            media_summary += f" x {len(media)}"
        if track_count:
            media_summary += f", {track_count} tracks"

        labels = []
        for label_info in candidate.get('label-info', []):
            label = (label_info.get('label') or {}).get('name')
            catalog_number = label_info.get('catalog-number')
            if label and catalog_number:
                labels.append(f"{label}: {catalog_number}")
            elif catalog_number:
                labels.append(catalog_number)
            elif label:
                labels.append(label)

        details = [candidate.get('country') or 'country unknown', candidate.get('date') or 'date unknown', media_summary]
        if labels:
            details.append('; '.join(labels))
        barcode = candidate.get('barcode')
        if barcode:
            details.append(f"barcode {barcode}")
        if release_id:
            details.append(release_id)
        prefix = 'Currently used | ' if release_id and release_id == current_id else ''
        return f"{prefix}{title} | " + ' | '.join(details)

    @classmethod
    def choose_linked_original(cls, api: PluginApi, album: Album) -> None:
        """Fetch linked original details and let the user choose a source edition."""
        if getattr(album, 'metadata', {}).get('releasestatus') != 'pseudo-release':
            return
        if getattr(album, 'id', '') in cls.in_flight_albums:
            return

        candidates = getattr(album, '_pseudo_original_candidates', [])
        if not candidates:
            return

        current_id = album.metadata.get(TAG_ORIGINAL_RELEASE_ID)
        resolved: dict[str, dict[str, Any]] = {}
        remaining = len(candidates)
        picker_token = object()
        picker_shown = False
        album._pseudo_original_picker_token = picker_token

        def show_picker() -> None:
            nonlocal picker_shown
            if picker_shown:
                return
            if getattr(album, '_pseudo_original_picker_token', None) is not picker_token:
                return
            picker_shown = True

            complete_candidates = [
                resolved.get(candidate.get('id'), candidate)
                for candidate in candidates
                if candidate.get('id')
            ]
            choices: list[tuple[str, str | None]] = [("Automatic best match", None)]
            for candidate in complete_candidates:
                choices.append((cls._format_original_candidate(candidate, current_id), candidate.get('id')))

            current_index = next(
                (index for index, (_, release_id) in enumerate(choices) if release_id == current_id),
                0,
            )
            labels = [label for label, _ in choices]
            selected_label, accepted = QtWidgets.QInputDialog.getItem(
                getattr(getattr(api, 'tagger', None), 'window', None),
                "Choose linked original",
                "Select the original edition for catalog metadata and cover art:",
                labels,
                current_index,
                False,
            )
            if not accepted:
                return

            selected_id = next((release_id for label, release_id in choices if label == selected_label), None)
            current_mode = getattr(album, '_pseudo_original_selection_mode', 'automatic')
            new_mode = 'manual' if selected_id else 'automatic'
            album._pseudo_original_selection_mode = new_mode
            album._pseudo_original_release_choice = selected_id
            if (
                selected_id == current_id
                and new_mode == current_mode
                and current_id
            ):
                return
            album.load(priority=True, refresh=True)

        def on_loaded(candidate: dict[str, Any], http: Any, error: Any, fallback: dict[str, Any]) -> None:
            nonlocal remaining
            if not error and candidate:
                resolved[candidate.get('id', '')] = candidate
            else:
                cls._log_debug(api, "Could not load linked original %s details", fallback.get('id'))
            remaining -= 1
            if remaining == 0:
                show_picker()

        for candidate in candidates:
            release_id = candidate.get('id')
            if not release_id:
                remaining -= 1
                continue
            api.mb_api.get_release_by_id(
                release_id,
                lambda document, http, error, fallback=candidate: on_loaded(document, http, error, fallback),
                inc=['labels', 'media', 'discids'],
            )

        if remaining <= 0:
            show_picker()

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

                supplement_pseudo_metadata(album.metadata, document)
                new_meta = getattr(album, '_new_metadata', None)
                if new_meta is not None:
                    supplement_pseudo_metadata(new_meta, document)
                cls._log_debug(api, "Supplemented pseudo-release %s with original %s", album_id, target_mbid)

            except Exception as exc:
                api.logger.error("Error processing pseudo-release enrichment: %s", exc)

            finally:
                cls.in_flight_albums.discard(album_id)
                if hasattr(api, 'complete_album_task'):
                    api.complete_album_task(album, task_id)
                if hasattr(album, '_finalize_loading'):
                    album._finalize_loading(None)

        if hasattr(api, 'add_album_task') and hasattr(api, 'mb_api'):
            api.add_album_task(
                album=album,
                task_id=task_id,
                description=f"Loading pseudo-release data for {target_mbid}",
                timeout=15.0,
                request_factory=lambda: api.mb_api.get_release_by_id(target_mbid, on_loaded, inc=inc),
                blocking=True,
            )

def enable(api: PluginApi) -> None:
    """Called when the plugin is enabled in Picard."""
    # Register default plugin configurations
    api.plugin_config.register_option(OPT_AUTO_SUPPLEMENT, True)

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
