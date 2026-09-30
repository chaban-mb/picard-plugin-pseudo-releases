# MusicBrainz Picard Plugin: Pseudo-Releases
#
# Copyright (C) 2026 Picard Community
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, see <https://www.gnu.org/licenses/>.

"""Pseudo-Releases Picard Plugin.

Supplements pseudo-releases with missing physical/catalog metadata and Cover Art Archive
artwork from original releases, and automatically translates loaded original releases
using pseudo-release tracklists and native translated join phrases.
"""

from collections.abc import Callable
from typing import Any

try:
    from picard.debug_opts import DebugOpt
    from picard.plugin3.api import (
        Album,
        Metadata,
        PluginApi,
        Track,
        t_,
    )
except ImportError:
    # Fallback types for unit testing outside Picard runtime
    class DebugOpt:
        PLUGIN_DEVELOPMENT = "plugin-development"

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
        select_best_pseudo_candidate,
    )
    from .constants import (
        OPT_AUTO_OVERLAY,
        OPT_AUTO_SUPPLEMENT,
        OPT_ENABLED,
        OPT_SKIP_LATIN_ORIGINALS,
        OPT_TARGET_SCRIPT_MODE,
        PSEUDO_RELEASE_STATUS,
        SCRIPT_MODE_LATN,
        TAG_ORIGINAL_RELEASE_ID,
        TAG_PSEUDO_RELEASE_ID,
        get_config_value,
    )
    from .metadata_engine import (
        overlay_pseudo_metadata_on_album,
        parse_artist_credit_node,
        supplement_pseudo_metadata,
    )
    from .options import PseudoReleaseOptionsPage
except (ImportError, ValueError):
    from caa_provider import PseudoReleaseCoverArtProvider
    from candidates import (
        find_related_releases,
        select_best_original_candidate,
        select_best_pseudo_candidate,
    )
    from constants import (
        OPT_AUTO_OVERLAY,
        OPT_AUTO_SUPPLEMENT,
        OPT_ENABLED,
        OPT_SKIP_LATIN_ORIGINALS,
        OPT_TARGET_SCRIPT_MODE,
        PSEUDO_RELEASE_STATUS,
        SCRIPT_MODE_LATN,
        TAG_ORIGINAL_RELEASE_ID,
        TAG_PSEUDO_RELEASE_ID,
        get_config_value,
    )
    from metadata_engine import (
        overlay_pseudo_metadata_on_album,
        parse_artist_credit_node,
        supplement_pseudo_metadata,
    )
    from options import PseudoReleaseOptionsPage


class ManifestTranslations:
    """Translation strings for the plugin manifest."""

    NAME = "Pseudo-Releases"
    DESC = (
        "Supplements pseudo-releases with original catalog metadata & cover art, and overlays translated tracklists."
    )


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
        if hasattr(album, '_pseudo_tracks'):
            album._pseudo_tracks = None
        if hasattr(album, '_pseudo_mbid'):
            album._pseudo_mbid = None

    @classmethod
    def process_album_metadata(
        cls,
        api: PluginApi,
        album: Album,
        album_metadata: Metadata,
        release_node: dict[str, Any],
    ) -> None:
        """Process loaded release to apply supplementation or translation overlays."""
        # Always reset cached pseudo-release state on the album object when loading or switching versions
        album._pseudo_tracks = None
        album._pseudo_mbid = None

        if not get_config_value(api.plugin_config, OPT_ENABLED, True):
            return

        album_id = getattr(album, 'id', '')
        if album_id in cls.in_flight_albums:
            return

        # Avoid re-processing already enriched albums
        if album_metadata.get(TAG_ORIGINAL_RELEASE_ID) or album_metadata.get(TAG_PSEUDO_RELEASE_ID):
            return

        is_pseudo = release_node.get('status') == PSEUDO_RELEASE_STATUS

        # DIRECTION 1: Supplement pseudo-release with original catalog metadata & cover art
        if is_pseudo and get_config_value(api.plugin_config, OPT_AUTO_SUPPLEMENT, True):
            cls._handle_supplement_pseudo(api, album, album_metadata, release_node)

        # DIRECTION 2: Overlay pseudo-release tracklist & artist credits onto original release
        elif not is_pseudo and get_config_value(api.plugin_config, OPT_AUTO_OVERLAY, True):
            cls._handle_overlay_original(api, album, album_metadata, release_node)

    @classmethod
    def _handle_supplement_pseudo(
        cls,
        api: PluginApi,
        album: Album,
        album_metadata: Metadata,
        release_node: dict[str, Any],
    ) -> None:
        """Direction 1: Find best matching original release and queue supplementation."""
        candidates = find_related_releases(release_node, direction='backward')
        if not candidates:
            cls._log_debug(api, "No backward transl-tracklisting relations found for %s", album.id)
            return

        files = getattr(album, 'iterfiles', lambda: [])() if hasattr(album, 'iterfiles') else []
        disc_ids = getattr(album, 'discids', None)

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
        cls._queue_enrichment(api, album, orig_id, is_overlay=False)

    @classmethod
    def _handle_overlay_original(
        cls,
        api: PluginApi,
        album: Album,
        album_metadata: Metadata,
        release_node: dict[str, Any],
    ) -> None:
        """Direction 2: Find best matching pseudo-release and queue translation overlay."""
        # Check if user opted to skip if original is already Latin script
        if get_config_value(api.plugin_config, OPT_SKIP_LATIN_ORIGINALS, True):
            text_rep = release_node.get('text-representation') or {}
            if (text_rep.get('script') or '').capitalize() == 'Latn':
                cls._log_debug(api, "Skipping translation overlay; original %s is already Latin script", album.id)
                return

        candidates = find_related_releases(release_node, direction='forward')
        if not candidates:
            cls._log_debug(api, "No forward transl-tracklisting relations found for %s", album.id)
            return

        target_mode = get_config_value(api.plugin_config, OPT_TARGET_SCRIPT_MODE, SCRIPT_MODE_LATN)
        best_pseudo = select_best_pseudo_candidate(candidates, target_mode=target_mode)

        if not best_pseudo or not best_pseudo.get('id'):
            return

        pseudo_id = best_pseudo['id']
        cls._log_debug(api, "Selected pseudo-release candidate %s for original %s", pseudo_id, album.id)
        cls._queue_enrichment(api, album, pseudo_id, is_overlay=True)

    @classmethod
    def _queue_enrichment(
        cls,
        api: PluginApi,
        album: Album,
        target_mbid: str,
        is_overlay: bool,
    ) -> None:
        """Fetch target release asynchronously using api.add_album_task with blocking=True."""
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

                if is_overlay:
                    overlay_pseudo_metadata_on_album(album, document)
                    cls._log_debug(api, "Overlaid pseudo-release %s onto %s", target_mbid, album_id)
                else:
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

    @classmethod
    def process_track_metadata(
        cls,
        api: PluginApi,
        track: Track,
        metadata: Metadata,
        track_node: dict[str, Any],
        release_node: dict[str, Any] | None = None,
    ) -> None:
        """Track metadata processor ensuring tracks of overlaid albums get pseudo translations."""
        if not get_config_value(api.plugin_config, OPT_ENABLED, True):
            return
        if not get_config_value(api.plugin_config, OPT_AUTO_OVERLAY, True):
            return

        # Direction 2 (overlay) is strictly for original releases overlaid with pseudo data.
        # It must NEVER modify native pseudo-releases.
        if release_node and release_node.get('status') == PSEUDO_RELEASE_STATUS:
            return

        album = getattr(track, 'album', None)
        if not album:
            return

        album_meta = getattr(album, 'metadata', None)
        if album_meta:
            if (
                album_meta.get('releasestatus') == PSEUDO_RELEASE_STATUS
                or album_meta.get('status') == PSEUDO_RELEASE_STATUS
            ):
                return
            pseudo_id = album_meta.get(TAG_PSEUDO_RELEASE_ID)
            if not pseudo_id:
                return
            if getattr(album, '_pseudo_mbid', None) != pseudo_id:
                return
        else:
            return

        pseudo_tracks = getattr(album, '_pseudo_tracks', None)
        if not pseudo_tracks:
            return

        rec_id = metadata.get('musicbrainz_recordingid') or (track_node.get('recording', {}).get('id') if isinstance(track_node, dict) else None)
        med_num = metadata.get('discnumber', '1')
        trk_num = metadata.get('tracknumber', '1')
        pos_key = f"{med_num}:{trk_num}"

        matched = pseudo_tracks.get(rec_id) or pseudo_tracks.get(pos_key)
        if not matched:
            return

        new_title = matched.get('title')
        if new_title:
            metadata['title'] = new_title

        if 'artist-credit' in matched:
            t_disp, t_sort, t_names = parse_artist_credit_node(matched['artist-credit'])
            if t_disp:
                metadata['artist'] = t_disp
            if t_sort:
                metadata['artistsort'] = t_sort
            if t_names:
                metadata['artists'] = t_names


def enable(api: PluginApi) -> None:
    """Called when the plugin is enabled in Picard."""
    # Register default plugin configurations
    api.plugin_config.register_option(OPT_ENABLED, True)
    api.plugin_config.register_option(OPT_AUTO_SUPPLEMENT, True)
    api.plugin_config.register_option(OPT_AUTO_OVERLAY, True)
    api.plugin_config.register_option(OPT_TARGET_SCRIPT_MODE, SCRIPT_MODE_LATN)
    api.plugin_config.register_option(OPT_SKIP_LATIN_ORIGINALS, True)

    plugin = PseudoReleasePlugin

    # Register album metadata processor
    api.register_album_metadata_processor(plugin.process_album_metadata, priority=50)

    # Register track metadata processor
    if hasattr(api, 'register_track_metadata_processor'):
        api.register_track_metadata_processor(plugin.process_track_metadata, priority=50)

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
