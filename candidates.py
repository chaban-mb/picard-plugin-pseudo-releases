from collections.abc import Sequence
from typing import Any

from picard.util import strip_non_alnum

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
    if not isinstance(release_node, dict):
        return candidates
    relations = release_node.get('relations')
    for rel in (relations if isinstance(relations, list) else []):
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


def _extract_tag_values(source: Any, tag_name: str) -> set[str]:
    """Extract non-empty lowercase string values for a tag from a metadata container."""
    meta = getattr(source, 'orig_metadata', None)
    if meta is None:
        meta = getattr(source, 'metadata', source)
    raw_vals = meta.getall(tag_name) if hasattr(meta, 'getall') else meta.get(tag_name, [])
    if isinstance(raw_vals, str):
        raw_vals = [raw_vals]
    if raw_vals is None:
        return set()
    return {str(v).strip().lower() for v in raw_vals if str(v).strip()}


def _get_tag_from_files_or_metadata(
    tag_name: str,
    album_metadata: Any = None,
    files: Sequence[Any] | None = None,
) -> set[str]:
    """Collect non-empty string values for a tag from files or album metadata."""
    values: set[str] = set()
    if files:
        for file in files:
            values.update(_extract_tag_values(file, tag_name))
    if not values and album_metadata is not None:
        values.update(_extract_tag_values(album_metadata, tag_name))
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
    if not isinstance(candidate, dict):
        return 0.0

    score = 0.0

    # 1. Disc ID Match (+100.0) - Exact hardware verification
    raw_media = candidate.get('media')
    media_list = [m for m in raw_media if isinstance(m, dict)] if isinstance(raw_media, list) else []

    if disc_ids:
        candidate_disc_ids: set[str] = set()
        for medium in media_list:
            discs = medium.get('discs')
            for disc in (discs if isinstance(discs, list) else []):
                if isinstance(disc, dict):
                    d_id = disc.get('id')
                    if d_id:
                        candidate_disc_ids.add(str(d_id).lower())
        for d in disc_ids:
            if str(d).lower() in candidate_disc_ids:
                score += 100.0
                break

    # 2. Medium Layout / Track Count Match (+40.0)
    # Checks if candidate media matches the file count or disc layout
    total_tracks = 0
    for m in media_list:
        tc = m.get('track-count')
        if tc is not None:
            try:
                total_tracks += int(tc)
                continue
            except (ValueError, TypeError):
                pass
        tracks_val = m.get('tracks')
        if isinstance(tracks_val, list):
            total_tracks += len(tracks_val)

    file_count = len(files) if (files and isinstance(files, (list, tuple, set))) else 0
    if file_count > 0 and total_tracks == file_count:
        score += 40.0

    # 3. Barcode Match (+30.0)
    candidate_barcode = candidate.get('barcode')
    if candidate_barcode:
        clean_candidate_bc = strip_non_alnum(str(candidate_barcode)).replace(" ", "").lower()
        file_barcodes = {
            strip_non_alnum(str(b)).replace(" ", "").lower()
            for b in _get_tag_from_files_or_metadata('barcode', album_metadata, files)
        }
        if clean_candidate_bc and clean_candidate_bc in file_barcodes:
            score += 30.0

    # 4. Release Date / Year Match (+20.0)
    candidate_date = str(candidate.get('date') or '')
    candidate_year = candidate_date[:4]
    if candidate_year:
        file_dates = (
            _get_tag_from_files_or_metadata('date', album_metadata, files)
            | _get_tag_from_files_or_metadata('originaldate', album_metadata, files)
            | _get_tag_from_files_or_metadata('year', album_metadata, files)
        )
        file_years = {d[:4] for d in file_dates if len(d) >= 4}
        if candidate_year in file_years:
            score += 20.0

    # 5. Media / Format Match (+20.0)
    candidate_formats: set[str] = set()
    for medium in media_list:
        fmt = medium.get('format')
        if fmt is not None:
            candidate_formats.add(str(fmt).lower())
    if candidate_formats:
        file_media = _get_tag_from_files_or_metadata('media', album_metadata, files)
        if candidate_formats.intersection(file_media):
            score += 20.0

    # 6. Catalog Number Match (+15.0)
    candidate_cat_nums: set[str] = set()
    raw_label_info = candidate.get('label-info')
    for label_info in (raw_label_info if isinstance(raw_label_info, list) else []):
        if isinstance(label_info, dict):
            cat = label_info.get('catalog-number')
            if cat is not None:
                candidate_cat_nums.add(str(cat).strip().lower())
    if candidate_cat_nums:
        file_cats = _get_tag_from_files_or_metadata('catalognumber', album_metadata, files)
        if candidate_cat_nums.intersection(file_cats):
            score += 15.0

    # 7. Official Status Priority (+15.0)
    # Prefer official releases over bootleg/promotional unless specified
    if candidate.get('status') == 'Official':
        score += 15.0

    # 8. Preferred Countries Match (+10.0)
    country = candidate.get('country')
    if country and preferred_countries:
        country_str = str(country).upper()
        pref_upper = [str(c).upper() for c in preferred_countries]
        if country_str in pref_upper:
            # Earlier in preference list gets a slightly higher priority
            idx = pref_upper.index(country_str)
            score += max(1.0, 10.0 - idx)

    # 9. Cover Art Archive Presence (+5.0)
    caa = candidate.get('cover-art-archive')
    if isinstance(caa, dict) and (caa.get('artwork') or caa.get('front')):
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
    valid_candidates = [c for c in (candidates or []) if isinstance(c, dict)]
    if not valid_candidates:
        return None

    ranked = sorted(
        valid_candidates,
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
