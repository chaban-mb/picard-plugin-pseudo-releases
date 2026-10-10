"""Metadata supplementation and overlay engine for pseudo-releases."""

from typing import Any

try:
    from .constants import (
        SUPPLEMENTARY_ALBUM_TAGS,
        SUPPLEMENTARY_MULTI_TAGS,
        TAG_ORIGINAL_RELEASE_ID,
    )
except (ImportError, ValueError):
    from constants import (
        SUPPLEMENTARY_ALBUM_TAGS,
        SUPPLEMENTARY_MULTI_TAGS,
        TAG_ORIGINAL_RELEASE_ID,
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
        extracted['originaldate'] = date

    country = release_node.get('country', '')
    if country:
        extracted['releasecountry'] = country

    barcode = release_node.get('barcode', '')
    if barcode:
        extracted['barcode'] = barcode

    # Extract media formats from media list
    media_list = release_node.get('media', [])
    formats: list[str] = []
    for medium in media_list:
        fmt = medium.get('format')
        if fmt and fmt not in formats:
            formats.append(fmt)
    if formats:
        extracted['media'] = "; ".join(formats)

    # Extract labels and catalog numbers
    label_info_list = release_node.get('label-info', [])
    labels: list[str] = []
    cat_nums: list[str] = []
    for label_info in label_info_list:
        lbl = label_info.get('label', {}).get('name') if label_info.get('label') else None
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


__all__ = ('extract_release_catalog_metadata', 'supplement_pseudo_metadata')





