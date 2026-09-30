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

"""Metadata supplementation and overlay engine for pseudo-releases."""

from collections.abc import Sequence
from typing import Any

try:
    from .constants import (
        SUPPLEMENTARY_ALBUM_TAGS,
        SUPPLEMENTARY_MULTI_TAGS,
        TAG_ORIGINAL_ALBUM_ARTIST,
        TAG_ORIGINAL_ALBUM_TITLE,
        TAG_ORIGINAL_RELEASE_ID,
        TAG_PSEUDO_RELEASE_ID,
    )
except (ImportError, ValueError):
    from constants import (
        SUPPLEMENTARY_ALBUM_TAGS,
        SUPPLEMENTARY_MULTI_TAGS,
        TAG_ORIGINAL_ALBUM_ARTIST,
        TAG_ORIGINAL_ALBUM_TITLE,
        TAG_ORIGINAL_RELEASE_ID,
        TAG_PSEUDO_RELEASE_ID,
    )



def parse_artist_credit_node(credit_list: Sequence[dict[str, Any]] | None) -> tuple[str, str, list[str]]:
    """Reconstruct display name, sort name, and artist list from an artist-credit node.

    Accurately handles native join phrases (e.g. ' feat. ', ' and ', ' with ') as
    provided by pseudo-releases, preserving them without delimiter truncation.

    Args:
        credit_list: Sequence of artist credit dicts from MusicBrainz JSON.

    Returns:
        tuple[str, str, list[str]]:
            - display_artist: Formatted string with join phrases (e.g., "Artist A feat. Artist B")
            - sort_artist: Formatted sort string with join phrases (e.g., "A, Artist feat. B, Artist")
            - artist_list: List of individual artist credit names for multi-valued tags
    """
    if not credit_list:
        return "", "", []

    display_parts: list[str] = []
    sort_parts: list[str] = []
    artist_names: list[str] = []

    for item in credit_list:
        if not isinstance(item, dict):
            continue

        artist_obj = item.get('artist') or {}
        name = item.get('name') or artist_obj.get('name', '')
        sort_name = artist_obj.get('sort-name') or name
        joinphrase = item.get('joinphrase', '')

        display_parts.append(name + joinphrase)
        sort_parts.append(sort_name + joinphrase)
        if name:
            artist_names.append(name)

    display_artist = "".join(display_parts).strip()
    sort_artist = "".join(sort_parts).strip()
    return display_artist, sort_artist, artist_names


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

    Direction 1 (Goal 1): Fills in missing barcode, date, country, label, catalog numbers,
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


def build_track_mapping(release_node: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build a lookup map of tracks from a release node keyed by recording MBID and position.

    Args:
        release_node: MusicBrainz API release dictionary.

    Returns:
        dict: Mapping of recording MBID -> track dictionary, plus fallback '(medium, position)' keys.
    """
    mapping: dict[str, dict[str, Any]] = {}
    media = release_node.get('media', [])

    for med_idx, medium in enumerate(media, 1):
        for trk_idx, track in enumerate(medium.get('tracks', []), 1):
            pos_key = f"{med_idx}:{track.get('position', trk_idx)}"
            mapping[pos_key] = track

            rec_id = track.get('recording', {}).get('id')
            if rec_id:
                mapping[rec_id] = track

        for trk_idx, track in enumerate(medium.get('data-tracks', []), 1):
            pos_key = f"{med_idx}:data-{track.get('position', trk_idx)}"
            mapping[pos_key] = track

            rec_id = track.get('recording', {}).get('id')
            if rec_id:
                mapping[rec_id] = track

    return mapping


def overlay_pseudo_metadata_on_album(album: Any, pseudo_node: dict[str, Any]) -> None:
    """Overlay pseudo-release titles and translated artist credits onto an original release.

    Direction 2 (Bonus Goal): Replaces release title, album artist, track titles, and track
    artist credits while retaining original physical catalog metadata.

    Args:
        album: Picard Album instance of the loaded original release.
        pseudo_node: MusicBrainz API dictionary of the source pseudo-release.
    """
    pseudo_id = pseudo_node.get('id', '')
    if not pseudo_id:
        return

    # Backup original titles if not already backed up
    if not album.metadata.get(TAG_ORIGINAL_ALBUM_TITLE):
        album.metadata[TAG_ORIGINAL_ALBUM_TITLE] = album.metadata.get('album', '')
    if not album.metadata.get(TAG_ORIGINAL_ALBUM_ARTIST):
        album.metadata[TAG_ORIGINAL_ALBUM_ARTIST] = album.metadata.get('albumartist', '')

    pseudo_title = pseudo_node.get('title')
    disp, sort, names = ("", "", [])
    if 'artist-credit' in pseudo_node:
        disp, sort, names = parse_artist_credit_node(pseudo_node['artist-credit'])

    # 1. Update album.metadata
    if pseudo_title:
        album.metadata['album'] = pseudo_title
    if disp:
        album.metadata['albumartist'] = disp
    if sort:
        album.metadata['albumartistsort'] = sort
    if names:
        album.metadata['albumartists'] = names
    album.metadata[TAG_PSEUDO_RELEASE_ID] = pseudo_id

    # 2. Update album._new_metadata if present (Picard assigns self.metadata = self._new_metadata in _finalize_loading_album)
    new_meta = getattr(album, '_new_metadata', None)
    if new_meta is not None:
        if pseudo_title:
            new_meta['album'] = pseudo_title
        if disp:
            new_meta['albumartist'] = disp
        if sort:
            new_meta['albumartistsort'] = sort
        if names:
            new_meta['albumartists'] = names
        new_meta[TAG_PSEUDO_RELEASE_ID] = pseudo_id

    # Build track lookup from pseudo-release
    pseudo_tracks = build_track_mapping(pseudo_node)
    album._pseudo_tracks = pseudo_tracks
    album._pseudo_mbid = pseudo_id

    # 3. Update album._release_node in-place if present
    # This is CRITICAL: in Picard's async loading pipeline, _load_tracks() creates Track objects
    # from album._release_node['media'] AFTER the critical task completes.
    release_node = getattr(album, '_release_node', None)
    if release_node:
        if pseudo_title:
            release_node['title'] = pseudo_title
        if 'artist-credit' in pseudo_node:
            release_node['artist-credit'] = pseudo_node['artist-credit']

        media = release_node.get('media', [])
        for med_idx, medium in enumerate(media, 1):
            for trk_idx, track_node in enumerate(medium.get('tracks', []), 1):
                rec_id = track_node.get('recording', {}).get('id')
                pos_key = f"{med_idx}:{track_node.get('position', trk_idx)}"
                matched = pseudo_tracks.get(rec_id) or pseudo_tracks.get(pos_key)
                if matched:
                    if matched.get('title'):
                        track_node['title'] = matched['title']
                    if 'artist-credit' in matched:
                        track_node['artist-credit'] = matched['artist-credit']

            for trk_idx, track_node in enumerate(medium.get('data-tracks', []), 1):
                rec_id = track_node.get('recording', {}).get('id')
                pos_key = f"{med_idx}:data-{track_node.get('position', trk_idx)}"
                matched = pseudo_tracks.get(rec_id) or pseudo_tracks.get(pos_key)
                if matched:
                    if matched.get('title'):
                        track_node['title'] = matched['title']
                    if 'artist-credit' in matched:
                        track_node['artist-credit'] = matched['artist-credit']

    # 4. If Track objects have ALREADY been instantiated (e.g. album.tracks or album._new_tracks)
    track_list = list(getattr(album, 'tracks', None) or [])
    for t in getattr(album, '_new_tracks', None) or []:
        if t not in track_list:
            track_list.append(t)

    for track in track_list:
        rec_id = track.metadata.get('musicbrainz_recordingid')
        med_num = track.metadata.get('discnumber', '1')
        trk_num = track.metadata.get('tracknumber', '1')
        pos_key = f"{med_num}:{trk_num}"

        matched_pseudo_track = pseudo_tracks.get(rec_id) or pseudo_tracks.get(pos_key)
        if not matched_pseudo_track:
            continue

        new_title = matched_pseudo_track.get('title')
        if new_title:
            track.metadata['title'] = new_title

        if 'artist-credit' in matched_pseudo_track:
            t_disp, t_sort, t_names = parse_artist_credit_node(matched_pseudo_track['artist-credit'])
            if t_disp:
                track.metadata['artist'] = t_disp
            if t_sort:
                track.metadata['artistsort'] = t_sort
            if t_names:
                track.metadata['artists'] = t_names

        # Keep original/base track metadata in sync
        if hasattr(track, 'orig_metadata'):
            track.orig_metadata.copy(track.metadata)

        # Notify files associated with this track (Picard Track uses .files)
        files = getattr(track, 'files', None) or getattr(track, 'linked_files', [])
        for file in files:
            if hasattr(track, 'update_file_metadata'):
                track.update_file_metadata(file)

        if hasattr(track, 'update'):
            track.update()

    if hasattr(album, 'update'):
        album.update()
