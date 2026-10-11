"""Pseudo-Releases core plugin orchestrator for catalog and cover-art supplementation."""

from typing import Any

try:
    from .compat import (
        Album,
        DebugOpt,
        Metadata,
        PluginApi,
        webbrowser2,
    )
    from .candidates import (
        find_related_releases,
        select_best_original_candidate,
    )
    from .constants import (
        PSEUDO_RELEASE_STATUS,
        TAG_ORIGINAL_RELEASE_ID,
        get_config_value,
    )
    from .metadata_engine import (
        get_enrichment_inc_params,
        supplement_pseudo_metadata,
        supplement_release_relationships_and_genres,
    )
except (ImportError, ValueError):
    from compat import (
        Album,
        DebugOpt,
        Metadata,
        PluginApi,
        webbrowser2,
    )
    from candidates import (
        find_related_releases,
        select_best_original_candidate,
    )
    from constants import (
        PSEUDO_RELEASE_STATUS,
        TAG_ORIGINAL_RELEASE_ID,
        get_config_value,
    )
    from metadata_engine import (
        get_enrichment_inc_params,
        supplement_pseudo_metadata,
        supplement_release_relationships_and_genres,
    )

try:
    from picard.mbjson import (
        countries_from_node,
        label_info_from_node,
        media_formats_from_node,
    )
    from picard.releasegroup import (
        VERSIONS_EXTRA_HEADINGS,
        VERSIONS_MAX_TRACKS,
    )
    from picard.util import countries_shortlist
    from picard.i18n import (
        gettext as _,
        pgettext_attributes,
    )
except (ImportError, AttributeError):
    def countries_from_node(node: dict[str, Any]) -> list[str]:
        countries: list[str] = []
        events = node.get("release-events") if isinstance(node, dict) else None
        for event in (events if isinstance(events, list) else []):
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
        if len(countries) <= 6:
            return "+".join(countries)
        return f"{'+'.join(countries[:3])}+…+{'+'.join(countries[-3:])}"

    def label_info_from_node(node: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
        labels: list[str] = []
        catalog_numbers: list[str] = []
        if not isinstance(node, list):
            return (labels, catalog_numbers)
        for label_info in node:
            if isinstance(label_info, dict):
                label_name = (label_info.get("label") or {}).get("name")
                catalog_number = label_info.get("catalog-number")
                if label_name and label_name not in labels:
                    labels.append(label_name)
                if catalog_number and catalog_number not in catalog_numbers:
                    catalog_numbers.append(catalog_number)
        return (labels, catalog_numbers)

    def media_formats_from_node(node: list[dict[str, Any]]) -> str:
        if not isinstance(node, list):
            return ""
        formats_count: dict[str, int] = {}
        formats_order: list[str] = []
        for medium in node:
            if not isinstance(medium, dict):
                continue
            text = medium.get("format", "(unknown)") or "(unknown)"
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
            album._pseudo_original_details = {}
            album._pseudo_candidate_stubs = {}
            album._pseudo_original_is_full = {}

        candidates = find_related_releases(release_node, direction='backward')
        album._pseudo_original_candidates = candidates

        selection_mode = getattr(album, '_pseudo_original_selection_mode', 'automatic')
        if selection_mode == 'manual':
            preferred_id = getattr(album, '_pseudo_original_release_choice', None)
        else:
            already_enriched_id = album_metadata.get(TAG_ORIGINAL_RELEASE_ID)
            if already_enriched_id:
                preferred_id = already_enriched_id
            else:
                files = getattr(album, 'iterfiles', lambda: [])() if hasattr(album, 'iterfiles') else []
                disc_ids = getattr(album, '_discids', None) or getattr(album, 'discids', None)
                tagger = getattr(api, 'tagger', None)
                config = getattr(tagger, 'config', None) or getattr(api, 'config', None)
                pref_countries = get_config_value(
                    getattr(config, 'setting', None) if config else None,
                    'preferred_release_countries',
                    [],
                )
                preferred = select_best_original_candidate(
                    candidates=candidates,
                    album_metadata=album_metadata,
                    files=list(files),
                    disc_ids=list(disc_ids) if disc_ids else None,
                    preferred_countries=pref_countries,
                )
                preferred_id = preferred.get('id') if preferred else None

        cls._prefetch_linked_original_details(api, album, candidates, preferred_id)

        already_enriched_id = album_metadata.get(TAG_ORIGINAL_RELEASE_ID)
        # Avoid re-processing already enriched albums after preserving chooser state.
        if already_enriched_id and selection_mode != 'manual':
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
        album_metadata[TAG_ORIGINAL_RELEASE_ID] = orig_id

        cached_release = getattr(album, '_pseudo_original_details', {}).get(orig_id)
        is_full = getattr(album, '_pseudo_original_is_full', {}).get(orig_id, False)
        if cached_release and is_full:
            supplement_pseudo_metadata(
                album_metadata,
                cached_release,
                set_original_id=True,
            )
            supplement_release_relationships_and_genres(
                album,
                cached_release,
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
        stub_cache = getattr(album, '_pseudo_candidate_stubs', None)
        if stub_cache is None:
            stub_cache = {}
            album._pseudo_candidate_stubs = stub_cache
        loading_ids = getattr(album, '_pseudo_original_details_loading_ids', None)
        if loading_ids is None:
            loading_ids = set()
            album._pseudo_original_details_loading_ids = loading_ids

        # Cap background prefetching to at most 3 fallback candidates to conserve rate limiter
        unfetched = [
            c for c in candidates
            if c.get('id')
            and c['id'] != preferred_id
            and c['id'] not in detail_cache
            and c['id'] not in stub_cache
            and c['id'] not in loading_ids
        ][:3]

        for fallback in unfetched:
            release_id = fallback['id']
            loading_ids.add(release_id)
            task_id = f"pseudo_prefetch_{release_id}"

            def on_loaded(
                document: dict[str, Any],
                http: Any,
                error: Any,
                fallback: dict[str, Any] = fallback,
                task_id: str = task_id,
            ) -> None:
                try:
                    loading_ids.discard(fallback['id'])
                    if not error and document:
                        stubs = getattr(album, '_pseudo_candidate_stubs', {})
                        stubs[fallback['id']] = document
                        album._pseudo_candidate_stubs = stubs
                finally:
                    if hasattr(api, 'complete_album_task'):
                        api.complete_album_task(album, task_id)

            if hasattr(api, 'add_album_task'):
                api.add_album_task(
                    album=album,
                    task_id=task_id,
                    description=f"Prefetching edition data for {release_id}",
                    timeout=10.0,
                    request_factory=lambda rel_id=release_id, cb=on_loaded: api.mb_api.get_release_by_id(
                        rel_id,
                        cb,
                        inc=['labels', 'media', 'discids'],
                    ),
                    blocking=False,
                )
            else:
                api.mb_api.get_release_by_id(
                    release_id,
                    on_loaded,
                    inc=['labels', 'media', 'discids'],
                )

    @staticmethod
    def _format_original_candidate(candidate: dict[str, Any]) -> str:
        """Format a compact edition label for the linked-original menu."""
        if not isinstance(candidate, dict):
            candidate = {}
        raw_media = candidate.get('media')
        media = [medium for medium in raw_media if isinstance(medium, dict)] if isinstance(raw_media, list) else []
        track_counts = [
            str(medium.get('track-count') or len(medium.get('tracks') or []))
            for medium in media
        ]
        valid_track_counts = [count for count in track_counts if count != '0']
        if len(valid_track_counts) > VERSIONS_MAX_TRACKS:
            tracks = '+'.join(valid_track_counts[:VERSIONS_MAX_TRACKS]) + '+…'
        else:
            tracks = '+'.join(valid_track_counts)
        year = (candidate.get('date') or '')[:4]

        rel_events = candidate.get('release-events')
        countries = countries_from_node(candidate) if isinstance(rel_events, list) else []
        if countries:
            country = countries_shortlist(countries)
        else:
            country = candidate.get('country') or '??'

        formats = media_formats_from_node(media)
        raw_label_infos = candidate.get('label-info')
        label_infos = (
            [item for item in raw_label_infos if isinstance(item, dict)]
            if isinstance(raw_label_infos, list)
            else []
        )
        labels, catalog_numbers = label_info_from_node(label_infos)

        parts = [
            tracks or '??',
            year or '????',
            country,
            formats or '(unknown format)',
            ', '.join(labels) if labels else '',
            ', '.join(catalog_numbers) if catalog_numbers else '',
        ]
        return ' / '.join(p for p in parts if p)

    @staticmethod
    def _format_original_candidate_tooltip(candidate: dict[str, Any]) -> str:
        """Format additional release details using Picard's Other versions fields."""
        if not isinstance(candidate, dict):
            candidate = {}
        packaging = pgettext_attributes('release_packaging', candidate.get('packaging', '') or '??')
        barcode = candidate.get('barcode', '') or _('[no barcode]')

        packaging_heading = _(VERSIONS_EXTRA_HEADINGS.get('packaging', 'Packaging'))
        barcode_heading = _(VERSIONS_EXTRA_HEADINGS.get('barcode', 'Barcode'))

        details = [
            f"{packaging_heading}: {packaging}",
            f"{barcode_heading}: {barcode}",
        ]
        disambiguation = candidate.get('disambiguation')
        if disambiguation:
            disambig_heading = _(VERSIONS_EXTRA_HEADINGS.get('disambiguation', 'Disambiguation'))
            details.append(f"{disambig_heading}: {disambiguation}")
        details.append("Middle-click or right-click to open in browser.")
        return '\n'.join(details)

    @classmethod
    def open_release_in_browser(cls, release_id: str, tagger: Any = None) -> None:
        """Open a release page in the MusicBrainz web browser."""
        tagger = tagger or getattr(cls.api, 'tagger', None)
        if tagger and hasattr(tagger, 'get_file_lookup'):
            tagger.get_file_lookup().album_lookup(release_id)
            return

        try:
            webbrowser2.open(f"https://musicbrainz.org/release/{release_id}")
        except Exception:
            import webbrowser

            webbrowser.open(f"https://musicbrainz.org/release/{release_id}")

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
        inc = list(get_enrichment_inc_params())

        # Determine authentication state for MusicBrainz web service
        tagger = getattr(api, 'tagger', None)
        webservice = getattr(tagger, 'webservice', None)
        oauth_mgr = getattr(webservice, 'oauth_manager', None)
        is_authorized = bool(
            oauth_mgr
            and hasattr(oauth_mgr, 'is_authorized')
            and oauth_mgr.is_authorized()
        )
        requires_auth = any(
            p in inc for p in ('user-tags', 'user-genres', 'user-ratings', 'user-collections')
        )

        # If user-specific tags were requested but client is not logged in,
        # fallback to public tags/genres so MusicBrainz does not reject with 401.
        if requires_auth and not is_authorized:
            inc = [
                'tags' if p == 'user-tags' else ('genres' if p == 'user-genres' else p)
                for p in inc
            ]
            requires_auth = False

        request_kwargs: dict[str, Any] = {'inc': inc}
        if requires_auth:
            request_kwargs['mblogin'] = True

        def on_loaded(document: dict[str, Any], http: Any, error: Any) -> None:
            try:
                if error:
                    api.logger.error("Failed to load release %s: %s", target_mbid, error)
                    return

                album._pseudo_original_details = getattr(album, '_pseudo_original_details', {})
                album._pseudo_original_details[target_mbid] = document
                is_full_map = getattr(album, '_pseudo_original_is_full', {})
                is_full_map[target_mbid] = True
                album._pseudo_original_is_full = is_full_map
                supplement_pseudo_metadata(
                    album.metadata,
                    document,
                    set_original_id=True,
                )
                new_meta = getattr(album, '_new_metadata', None)
                if new_meta is not None:
                    supplement_pseudo_metadata(
                        new_meta,
                        document,
                        set_original_id=True,
                    )
                supplement_release_relationships_and_genres(
                    album,
                    document,
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

        if hasattr(api, 'add_album_task') and hasattr(api, 'mb_api'):
            api.add_album_task(
                album=album,
                task_id=task_id,
                description=f"Loading pseudo-release data for {target_mbid}",
                timeout=15.0,
                request_factory=lambda: api.mb_api.get_release_by_id(
                    target_mbid,
                    on_loaded,
                    **request_kwargs,
                ),
                blocking=True,
            )
