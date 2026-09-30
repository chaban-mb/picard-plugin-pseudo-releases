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

"""Constants and configuration defaults for the Pseudo-Releases plugin."""

# MusicBrainz Relationship Type UUID for "transl-tracklisting"
# Forward phrase: "transliterated/translated track listings" (Original -> Pseudo)
# Reverse phrase: "transliterated/translated track listing of" (Pseudo -> Original)
RELATIONSHIP_TYPE_TRANSL_TRACKLISTING = 'fc399d47-23a7-4c28-bfcf-0607a562b644'

# MusicBrainz Release Status string for pseudo-releases
PSEUDO_RELEASE_STATUS = 'Pseudo-Release'

# Plugin configuration keys
OPT_AUTO_SUPPLEMENT = 'auto_supplement_pseudo'

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


def get_config_value(cfg, key, default=None):
    """Safe lookup for Picard plugin_config, supporting ProfileConfigSection (__getitem__)
    as well as standard dicts and objects implementing .get()."""
    if hasattr(cfg, 'get'):
        try:
            return cfg.get(key, default)
        except Exception:
            pass
    try:
        val = cfg[key]
        return val if val is not None else default
    except (KeyError, TypeError, IndexError):
        return default

