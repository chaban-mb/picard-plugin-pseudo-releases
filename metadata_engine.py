"""Metadata supplementation and overlay engine for pseudo-releases."""

from typing import Any

try:
    from picard import config
except ImportError:
    config = None  # type: ignore[assignment]

try:
    from .constants import (
        SUPPLEMENTARY_ALBUM_TAGS,
        SUPPLEMENTARY_MULTI_TAGS,
        TAG_ORIGINAL_RELEASE_ID,
        get_config_value,
    )
except (ImportError, ValueError):
    from constants import (
        SUPPLEMENTARY_ALBUM_TAGS,
        SUPPLEMENTARY_MULTI_TAGS,
        TAG_ORIGINAL_RELEASE_ID,
        get_config_value,
    )


def extract_release_catalog_metadata(release_node: dict[str, Any]) -> dict[str, Any]:
    """Extract physical and manufacturing catalog metadata from a release node.

    Args:
        release_node: MusicBrainz API release dictionary.

    Returns:
        dict[str, Any]: Extracted metadata fields (date, barcode, labels, formats, etc.).
    """
    extracted: dict[str, Any] = {}

    date = release_node.get('date', '')
    if date:
        extracted['date'] = date

    country = release_node.get('country', '')
    if country:
        extracted['releasecountry'] = country

    barcode = release_node.get('barcode', '')
    if barcode:
        extracted['barcode'] = barcode

    # Extract media formats from media list
    media_list = release_node.get('media') or []
    formats: list[str] = []
    for medium in media_list:
        if isinstance(medium, dict):
            fmt = medium.get('format')
            if fmt and fmt not in formats:
                formats.append(fmt)
    if formats:
        extracted['media'] = "; ".join(formats)

    # Extract labels and catalog numbers
    label_info_list = release_node.get('label-info') or []
    labels: list[str] = []
    cat_nums: list[str] = []
    for label_info in label_info_list:
        if isinstance(label_info, dict):
            lbl = label_info.get('label', {}).get('name') if isinstance(label_info.get('label'), dict) else None
            if lbl and lbl not in labels:
                labels.append(lbl)
            cat = label_info.get('catalog-number')
            if cat and cat not in cat_nums:
                cat_nums.append(cat)

    if labels:
        extracted['label'] = labels
    if cat_nums:
        extracted['catalognumber'] = cat_nums

    return extracted


def supplement_pseudo_metadata(
    album_metadata: Any,
    orig_release_node: dict[str, Any],
    preserve_existing: bool = False,
    set_original_id: bool = True,
) -> None:
    """Supplement a pseudo-release's metadata with catalog data from an original release.

    Direction 1: Populates barcode, date, country, label, catalog numbers,
    media formats, and optionally sets the original MBID reference.

    Args:
        album_metadata: Picard Metadata instance of the loaded pseudo-release.
        orig_release_node: MusicBrainz API dictionary of the source original release.
        preserve_existing: If True, only fills missing tags. If False (default),
                           overwrites existing pseudo-release tags.
        set_original_id: If True (default), sets the ~original_musicbrainz_albumid tag.
    """
    catalog_data = extract_release_catalog_metadata(orig_release_node)

    for tag in SUPPLEMENTARY_ALBUM_TAGS:
        val = catalog_data.get(tag)
        if not val:
            continue
        if preserve_existing and album_metadata.get(tag):
            continue
        album_metadata[tag] = val

    for tag in SUPPLEMENTARY_MULTI_TAGS:
        val_list = catalog_data.get(tag)
        if not val_list:
            continue
        if preserve_existing and album_metadata.getall(tag):
            continue
        album_metadata[tag] = val_list

    orig_id = orig_release_node.get('id')
    if orig_id and set_original_id:
        album_metadata[TAG_ORIGINAL_RELEASE_ID] = orig_id


def get_enrichment_inc_params(config_obj: Any = None) -> list[str]:
    """Determine the inc parameters to fetch for original release enrichment.

    Respects Picard core options:
    - config.setting['release_ars']: release-level relationships
    - config.setting['use_genres']: folksonomy tags and genres
    """
    target_config = config_obj if config_obj is not None else config
    setting = getattr(target_config, 'setting', None) if target_config else None

    inc = [
        'artists',
        'labels',
        'media',
        'discids',
        'release-rels',
        'artist-credits',
    ]

    # "Use release relationships" in Options -> Metadata
    if get_config_value(setting, 'release_ars', False):
        inc.extend([
            'artist-rels',
            'url-rels',
            'series-rels',
            'label-rels',
        ])

    # "Use genres from MusicBrainz" in Options -> Metadata -> Genres
    if get_config_value(setting, 'use_genres', False):
        if get_config_value(setting, 'only_my_genres', False):
            inc.extend(['user-tags', 'user-genres'])
        else:
            inc.extend(['tags', 'genres'])

    return inc


def supplement_release_relationships_and_genres(
    album: Any,
    orig_release_node: dict[str, Any],
    config_obj: Any = None,
) -> None:
    """Supplement release-level relationships and folksonomy tags/genres onto an album.

    Respects Picard core options:
    - config.setting['release_ars']: governs release relationship importing
    - config.setting['use_genres']: governs folksonomy tags and genres importing
    """
    target_config = config_obj if config_obj is not None else config
    setting = getattr(target_config, 'setting', None) if target_config else None

    # 1. Merge relationships into album._release_node['relations']
    orig_relations = orig_release_node.get('relations') or []
    if orig_relations and hasattr(album, '_release_node') and isinstance(album._release_node, dict):
        existing_rels = album._release_node.setdefault('relations', [])
        existing_signatures = set()
        for r in existing_rels or []:
            if isinstance(r, dict):
                target_type = r.get('target-type', '')
                target_val = r.get(target_type)
                target_id = target_val.get('id') if isinstance(target_val, dict) else None
                existing_signatures.add((r.get('type'), r.get('direction'), target_type, target_id))

        for rel in orig_relations:
            if not isinstance(rel, dict):
                continue
            # Skip reciprocal transl-tracklisting link back to the pseudo-release
            if rel.get('type') == 'transl-tracklisting':
                continue
            target_type = rel.get('target-type', '')
            target_val = rel.get(target_type)
            target_id = target_val.get('id') if isinstance(target_val, dict) else None
            sig = (rel.get('type'), rel.get('direction'), target_type, target_id)
            if sig not in existing_signatures:
                existing_rels.append(rel)
                existing_signatures.add(sig)

    # 2. Release relationships to metadata
    if get_config_value(setting, 'release_ars', False) and orig_relations:
        try:
            from picard.mbjson import _relations_to_metadata

            if hasattr(album, 'metadata'):
                _relations_to_metadata(orig_relations, album.metadata, config=target_config, entity='release')
            new_meta = getattr(album, '_new_metadata', None)
            if new_meta is not None:
                _relations_to_metadata(orig_relations, new_meta, config=target_config, entity='release')
        except Exception:
            pass

    # 3. Folksonomy tags and genres
    if get_config_value(setting, 'use_genres', False):
        if hasattr(album, '_release_node') and isinstance(album._release_node, dict):
            orig_tags = orig_release_node.get('tags') or []
            if orig_tags:
                album._release_node.setdefault('tags', []).extend(
                    [t for t in orig_tags if t not in (album._release_node.get('tags') or [])]
                )
            orig_genres = orig_release_node.get('genres') or []
            if orig_genres:
                album._release_node.setdefault('genres', []).extend(
                    [g for g in orig_genres if g not in (album._release_node.get('genres') or [])]
                )

        try:
            from picard.mbjson import add_genres_from_node

            add_genres_from_node(orig_release_node, album)
        except Exception:
            if hasattr(album, 'add_folksonomy_tag') and orig_release_node.get('tags'):
                for tag in orig_release_node['tags']:
                    album.add_folksonomy_tag(tag.get('name'), tag.get('count', 1))
            if hasattr(album, 'add_genre') and orig_release_node.get('genres'):
                for genre in orig_release_node['genres']:
                    album.add_genre(genre.get('name'), genre.get('count', 1))

        # Update tracks on the album to calculate merged genres / folksonomy tags
        tracks = getattr(album, 'tracks', [])
        for track in tracks:
            if hasattr(track, '_convert_folksonomy_tags_to_genre'):
                track._convert_folksonomy_tags_to_genre()
            if hasattr(track, '_add_folksonomy_tags_variable'):
                track._add_folksonomy_tags_variable()
            if hasattr(track, '_add_genres_variable'):
                track._add_genres_variable()


__all__ = (
    'extract_release_catalog_metadata',
    'get_enrichment_inc_params',
    'supplement_pseudo_metadata',
    'supplement_release_relationships_and_genres',
)





