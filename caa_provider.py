"""Cover Art Archive provider for pseudo-releases resolving artwork via original releases."""

from typing import Any

from picard.coverart.providers.caa import CoverArtProviderCaa
from picard.plugin3.api import t_


try:
    from .constants import (
        TAG_ORIGINAL_RELEASE_ID,
    )
except (ImportError, ValueError):
    from constants import (
        TAG_ORIGINAL_RELEASE_ID,
    )


class PseudoReleaseCoverArtProvider(CoverArtProviderCaa):
    """Cover Art Archive provider that downloads artwork for pseudo-releases
    using the linked original release MBID.
    """

    NAME = "pseudo_release_caa"
    TITLE = t_("provider.caa.title", "Cover Art Archive: Pseudo-Release (Original)")
    OPTIONS = None

    ignore_json_not_found_error = True

    @property
    def _original_id(self) -> str | None:
        """Resolve the linked original release ID from metadata or album state."""
        orig_id = self.metadata.get(TAG_ORIGINAL_RELEASE_ID)
        if orig_id:
            return orig_id
        if self.album:
            return getattr(self.album, '_pseudo_original_id', getattr(self.album, '_pseudo_original_release_choice', None))
        return None

    @property
    def original_release(self) -> dict[str, Any] | None:
        """Retrieve original release document from album cache if available."""
        orig_id = self._original_id
        if not orig_id or not self.album:
            return None
        details = getattr(self.album, '_pseudo_original_details', {})
        return details.get(orig_id)

    @property
    def _caa_path(self) -> str:
        """Route CAA request to the original release MBID if available."""
        orig_id = self._original_id
        if orig_id:
            return f"/release/{orig_id}/"
        return super()._caa_path

    @property
    def _has_suitable_artwork(self) -> bool:
        """Check if original release has artwork available in CAA."""
        orig_id = self._original_id
        if not orig_id:
            return False

        orig_release = self.original_release
        if orig_release and isinstance(orig_release, dict) and 'cover-art-archive' in orig_release:
            orig_node = self.release
            try:
                self.release = orig_release
                return super()._has_suitable_artwork
            finally:
                self.release = orig_node
        # If original release details are not yet cached, query CAA using original MBID
        return True

    def enabled(self) -> bool:
        """Activate for pseudo-releases that have resolved an original release candidate."""
        if not self._original_id or not super().enabled():
            return False
        return self._has_suitable_artwork

