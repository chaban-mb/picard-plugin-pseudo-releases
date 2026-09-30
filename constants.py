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

