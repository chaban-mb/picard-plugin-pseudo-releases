"""Constants and configuration defaults for the Pseudo-Releases plugin."""

# MusicBrainz Relationship Type UUID for "transl-tracklisting"
# Forward phrase: "transliterated/translated track listings" (Original -> Pseudo)
# Reverse phrase: "transliterated/translated track listing of" (Pseudo -> Original)
RELATIONSHIP_TYPE_TRANSL_TRACKLISTING = 'fc399d47-23a7-4c28-bfcf-0607a562b644'

# MusicBrainz Release Status string for pseudo-releases
PSEUDO_RELEASE_STATUS = 'Pseudo-Release'

# Metadata keys supplemented on pseudo-releases from original releases
SUPPLEMENTARY_ALBUM_TAGS = (
    'date',
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
    """Safe lookup for Picard config.setting, ProfileConfigSection, or dict-like objects."""
    if cfg is None:
        return default
    if hasattr(cfg, 'get'):
        return cfg.get(key, default)
    try:
        val = cfg[key]
        return val if val is not None else default
    except (KeyError, TypeError, IndexError):
        return default


