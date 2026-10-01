"""Cover Art Archive provider for pseudo-releases resolving artwork via original releases."""

from typing import Any

try:
    from picard.coverart.providers.caa import CoverArtProviderCaa
    from picard.i18n import N_
except ImportError:
    # Fallback base class for isolated unit testing
    class CoverArtProviderCaa:  # type: ignore[no-redef]
        NAME = "Cover Art Archive"
        TITLE = "Cover Art Archive: Release"
        OPTIONS = None

        def __init__(self, coverart: Any = None) -> None:
            self.coverart = coverart
            self.metadata: dict[str, Any] = {}
            self.release: dict[str, Any] = {}

        def enabled(self) -> bool:
            return True

        @property
        def _caa_path(self) -> str:
            return f"/release/{self.metadata.get('musicbrainz_albumid', '')}/"

        @property
        def _has_suitable_artwork(self) -> bool:
            caa = self.release.get('cover-art-archive', {})
            return bool(caa.get('artwork'))

    def N_(text: str) -> str:
        return text

try:
    from .constants import TAG_ORIGINAL_RELEASE_ID
except (ImportError, ValueError):
    from constants import TAG_ORIGINAL_RELEASE_ID


class PseudoReleaseCoverArtProvider(CoverArtProviderCaa):
    """Cover Art Archive provider that downloads artwork for pseudo-releases
    using the linked original release MBID.
    """

    NAME = "pseudo_release_caa"
    TITLE = N_("Cover Art Archive (via Original Release)")
    OPTIONS = None

    ignore_json_not_found_error = True

    @property
    def original_release(self) -> dict[str, Any] | None:
        """Retrieve original release document from album cache if available."""
        orig_id = self.metadata.get(TAG_ORIGINAL_RELEASE_ID)
        if not orig_id:
            return None
        album = getattr(self, 'album', None)
        if not album and hasattr(self, 'coverart') and self.coverart:
            album = getattr(self.coverart, 'album', None)
        if album:
            details = getattr(album, '_pseudo_original_details', {})
            return details.get(orig_id)
        return None

    @property
    def _caa_path(self) -> str:
        """Route CAA request to the original release MBID if available."""
        orig_id = self.metadata.get(TAG_ORIGINAL_RELEASE_ID)
        if orig_id:
            return f"/release/{orig_id}/"
        return super()._caa_path

    @property
    def _has_suitable_artwork(self) -> bool:
        """Check if original release has artwork available in CAA.

        If full original release details are cached, inspect the original release's
        'cover-art-archive' block (respecting user type restrictions).
        Otherwise, if TAG_ORIGINAL_RELEASE_ID is known, return True to allow
        querying coverartarchive.org directly (ignore_json_not_found_error handles 404s).
        """
        orig_id = self.metadata.get(TAG_ORIGINAL_RELEASE_ID)
        if not orig_id:
            return False

        orig_release = self.original_release
        if orig_release and 'cover-art-archive' in orig_release:
            orig_node = self.release
            try:
                self.release = orig_release
                return super()._has_suitable_artwork
            finally:
                self.release = orig_node

        if 'cover-art-archive' in self.release:
            return super()._has_suitable_artwork

        return True

    def enabled(self) -> bool:
        """Activate for pseudo-releases that have resolved an original release candidate."""
        if not self.metadata.get(TAG_ORIGINAL_RELEASE_ID):
            return False
        if hasattr(self, 'coverart') and self.coverart:
            if getattr(self.coverart, 'front_image_found', False):
                return False
        return self._has_suitable_artwork
