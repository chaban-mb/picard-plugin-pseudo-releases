# MusicBrainz Picard Plugin: Pseudo-Releases
#
# Copyright (C) 2026 Picard Community
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

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


def supplement_pseudo_metadata(album_metadata: Any, orig_release_node: dict[str, Any]) -> None:
    """Supplement a pseudo-release's metadata with catalog data from an original release.

    Direction 1: Fills in missing barcode, date, country, label, catalog numbers,
    media formats, and sets the original MBID reference.

    Args:
        album_metadata: Picard Metadata instance of the loaded pseudo-release.
        orig_release_node: MusicBrainz API dictionary of the source original release.
    """
    catalog_data = extract_release_catalog_metadata(orig_release_node)

    for tag in SUPPLEMENTARY_ALBUM_TAGS:
        val = catalog_data.get(tag)
        if val and not album_metadata.get(tag):
            album_metadata[tag] = val

    for tag in SUPPLEMENTARY_MULTI_TAGS:
        val_list = catalog_data.get(tag)
        if val_list and not album_metadata.getall(tag):
            album_metadata[tag] = val_list

    orig_id = orig_release_node.get('id')
    if orig_id:
        album_metadata[TAG_ORIGINAL_RELEASE_ID] = orig_id


__all__ = ('extract_release_catalog_metadata', 'supplement_pseudo_metadata')





