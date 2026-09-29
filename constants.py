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

"""Constants and configuration defaults for the Pseudo-Releases plugin."""

# MusicBrainz Relationship Type UUID for "transl-tracklisting"
# Forward phrase: "transliterated/translated track listings" (Original -> Pseudo)
# Reverse phrase: "transliterated/translated track listing of" (Pseudo -> Original)
RELATIONSHIP_TYPE_TRANSL_TRACKLISTING = 'fc399d47-23a7-4c28-bfcf-0607a562b644'

# MusicBrainz Release Status string for pseudo-releases
PSEUDO_RELEASE_STATUS = 'Pseudo-Release'

# Plugin configuration keys
OPT_ENABLED = 'enabled'
OPT_AUTO_SUPPLEMENT = 'auto_supplement_pseudo'
OPT_AUTO_OVERLAY = 'auto_apply_translations'
OPT_TARGET_SCRIPT_MODE = 'target_script_mode'
OPT_SKIP_LATIN_ORIGINALS = 'skip_latin_originals'

# Target script preferences
SCRIPT_MODE_LATN = 'latn'       # Prioritize Latin script / Romaji transliterations
SCRIPT_MODE_ENG = 'eng'         # Prioritize English translations
SCRIPT_MODE_LOCALES = 'locales' # Match Picard user interface language preferences

# Metadata keys supplemented on pseudo-releases from original releases
SUPPLEMENTARY_ALBUM_TAGS = (
    'date',
    'originaldate',
    'releasecountry',
    'barcode',
    'media',
)

SUPPLEMENTARY_MULTI_TAGS = (
    'label',
    'catalognumber',
)

# Custom internal / hidden metadata tags
TAG_ORIGINAL_RELEASE_ID = '~original_musicbrainz_albumid'
TAG_PSEUDO_RELEASE_ID = '~pseudo_musicbrainz_albumid'
TAG_ORIGINAL_ALBUM_TITLE = '~original_album'
TAG_ORIGINAL_ALBUM_ARTIST = '~original_albumartist'
