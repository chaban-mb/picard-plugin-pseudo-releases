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

    @property
    def _caa_path(self) -> str:
        """Route CAA request to the original release MBID if available."""
        orig_id = self.metadata.get(TAG_ORIGINAL_RELEASE_ID)
        if orig_id:
            return f"/release/{orig_id}/"
        return super()._caa_path

    @property
    def _has_suitable_artwork(self) -> bool:
        """Check if original release has artwork available in CAA."""
        if not self.metadata.get(TAG_ORIGINAL_RELEASE_ID):
            return False
        return super()._has_suitable_artwork

    def enabled(self) -> bool:
        """Only activate for pseudo-releases that have resolved an original release."""
        if not self.metadata.get(TAG_ORIGINAL_RELEASE_ID):
            return False
        return super().enabled()
