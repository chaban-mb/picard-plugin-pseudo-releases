"""Candidate discovery, ranking, and disambiguation algorithms."""

from collections.abc import Sequence
from typing import Any

try:
    from .constants import (
        RELATIONSHIP_TYPE_TRANSL_TRACKLISTING,
    )
except (ImportError, ValueError):
    from constants import (
        RELATIONSHIP_TYPE_TRANSL_TRACKLISTING,
    )


def find_related_releases(
    release_node: dict[str, Any],
    direction: str | None = None,
    rel_type: str = RELATIONSHIP_TYPE_TRANSL_TRACKLISTING,
) -> list[dict[str, Any]]:
    """Extract linked release objects from a release's relations list.

    Args:
        release_node: MusicBrainz API release dictionary.
        direction: Optional direction filter: 'forward' (Original -> Pseudo),
                   'backward' (Pseudo -> Original), or None for all directions.
        rel_type: Relationship UUID or type name (defaults to transl-tracklisting).

    Returns:
        list[dict[str, Any]]: List of target release dictionaries.
    """
    candidates: list[dict[str, Any]] = []
    relations = release_node.get('relations', [])
    for rel in relations:
        if not isinstance(rel, dict):
            continue

        r_type = rel.get('type')
        r_type_id = rel.get('type-id')
        if r_type != 'transl-tracklisting' and r_type_id != rel_type:
            continue

        if direction and rel.get('direction') != direction:
            continue

        target_release = rel.get('release')
        if target_release and isinstance(target_release, dict):
            candidates.append(target_release)

    return candidates


def _get_tag_from_files_or_metadata(
    tag_name: str,
    album_metadata: Any = None,
    files: Sequence[Any] | None = None,
) -> set[str]:
    """Collect non-empty string values for a tag from files or album metadata."""
    values: set[str] = set()

    if files:
        for file in files:
            meta = getattr(file, 'metadata', file)
            if hasattr(meta, 'getall'):
                for value in meta.getall(tag_name):
                    value = str(value).strip()
                    if value:
                        values.add(value.lower())
            elif hasattr(meta, 'get'):
                value = meta.get(tag_name)
                if value:
                    values.add(str(value).strip().lower())

    if not values and album_metadata is not None:
        if hasattr(album_metadata, 'getall'):
            for value in album_metadata.getall(tag_name):
                value = str(value).strip()
                if value:
                    values.add(value.lower())
        elif hasattr(album_metadata, 'get'):
            value = album_metadata.get(tag_name)
            if value:
                values.add(str(value).strip().lower())

    return values


def score_original_candidate(
    candidate: dict[str, Any],
    album_metadata: Any = None,
    files: Sequence[Any] | None = None,
    disc_ids: Sequence[str] | None = None,
    preferred_countries: Sequence[str] | None = None,
) -> float:
    """Score an original release candidate against local files and metadata.



    Discriminates between multi-format editions ($N \\to 1$) where track durations
    cannot distinguish identical audio recordings.

    Args:
        candidate: Candidate release dictionary from MusicBrainz API.
        album_metadata: Optional loaded album metadata.
        files: Optional list of audio files loaded into the album.
        disc_ids: Optional list of optical disc IDs (TOC).
        preferred_countries: Optional user preferred release country codes.

    Returns:
        float: Match score (higher is better).
    """
    score = 0.0

    # 1. Disc ID Match (+100.0) - Exact hardware verification
    if disc_ids:
        candidate_disc_ids: set[str] = set()
        for medium in candidate.get('media', []):
            for disc in medium.get('discs', []):
                d_id = disc.get('id')
                if d_id:
                    candidate_disc_ids.add(d_id.lower())
        for d in disc_ids:
            if d.lower() in candidate_disc_ids:
                score += 100.0
                break

    # 2. Medium Layout / Track Count Match (+40.0)
    # Checks if candidate media matches the file count or disc layout
    media_list = candidate.get('media', [])
    total_tracks = sum(m.get('track-count', len(m.get('tracks', []))) for m in media_list)
    file_count = len(files) if files else 0
    if file_count > 0 and total_tracks == file_count:
        score += 40.0

    # 3. Barcode Match (+30.0)
    candidate_barcode = candidate.get('barcode')
    if candidate_barcode:
        file_barcodes = _get_tag_from_files_or_metadata('barcode', album_metadata, files)
        if candidate_barcode.strip().lower() in file_barcodes:
            score += 30.0

    # 4. Media / Format Match (+20.0)
    candidate_formats: set[str] = set()
    for medium in media_list:
        fmt = medium.get('format')
        if fmt:
            candidate_formats.add(fmt.lower())
    if candidate_formats:
        file_media = _get_tag_from_files_or_metadata('media', album_metadata, files)
        if candidate_formats.intersection(file_media):
            score += 20.0

    # 5. Catalog Number Match (+15.0)
    candidate_cat_nums: set[str] = set()
    for label_info in candidate.get('label-info', []):
        cat = label_info.get('catalog-number')
        if cat:
            candidate_cat_nums.add(cat.strip().lower())
    if candidate_cat_nums:
        file_cats = _get_tag_from_files_or_metadata('catalognumber', album_metadata, files)
        if candidate_cat_nums.intersection(file_cats):
            score += 15.0

    # 6. Official Status Priority (+15.0)
    # Prefer official releases over bootleg/promotional unless specified
    if candidate.get('status') == 'Official':
        score += 15.0

    # 7. Preferred Countries Match (+10.0)
    country = candidate.get('country')
    if country and preferred_countries:
        pref_upper = [c.upper() for c in preferred_countries]
        if country.upper() in pref_upper:
            # Earlier in preference list gets a slightly higher priority
            idx = pref_upper.index(country.upper())
            score += max(1.0, 10.0 - idx)

    # 8. Cover Art Archive Presence (+5.0)
    caa = candidate.get('cover-art-archive', {})
    if caa.get('artwork') or caa.get('front'):
        score += 5.0

    return score


def select_best_original_candidate(
    candidates: Sequence[dict[str, Any]],
    album_metadata: Any = None,
    files: Sequence[Any] | None = None,
    disc_ids: Sequence[str] | None = None,
    preferred_countries: Sequence[str] | None = None,
) -> dict[str, Any] | None:
    """Rank and select the most promising original release from candidates."""
    if not candidates:
        return None

    ranked = sorted(
        candidates,
        key=lambda candidate: score_original_candidate(
            candidate=candidate,
            album_metadata=album_metadata,
            files=files,
            disc_ids=disc_ids,
            preferred_countries=preferred_countries,
        ),
        reverse=True,
    )
    return ranked[0]
