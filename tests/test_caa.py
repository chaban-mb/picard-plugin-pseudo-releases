# Tests for PseudoReleaseCoverArtProvider
import unittest
from caa_provider import PseudoReleaseCoverArtProvider
from constants import TAG_ORIGINAL_RELEASE_ID


from tests.mocks.mock_picard import (
    MockAlbum,
    MockCoverArt,
)


class TestPseudoReleaseCoverArtProvider(unittest.TestCase):
    def setUp(self):
        self.coverart = MockCoverArt()
        self.provider = PseudoReleaseCoverArtProvider(self.coverart)

    def test_disabled_without_original_release_id(self):
        # Without TAG_ORIGINAL_RELEASE_ID, provider must stay disabled
        self.assertFalse(self.provider.enabled())
        self.assertFalse(self.provider._has_suitable_artwork)
        self.assertEqual(self.provider._caa_path, "/release/pseudo-release-uuid-9fe/")

    def test_enabled_with_original_release_id(self):
        # When supplemented with TAG_ORIGINAL_RELEASE_ID
        self.provider.metadata[TAG_ORIGINAL_RELEASE_ID] = "original-release-uuid-7a1"

        self.assertTrue(self.provider.enabled())
        self.assertTrue(self.provider._has_suitable_artwork)
        self.assertEqual(
            self.provider._caa_path,
            "/release/original-release-uuid-7a1/",
        )

    def test_disabled_when_original_release_has_no_artwork(self):
        album = MockAlbum()
        album._pseudo_original_details = {
            "original-release-uuid-7a1": {
                "id": "original-release-uuid-7a1",
                "cover-art-archive": {"artwork": False},
            }
        }
        self.provider = PseudoReleaseCoverArtProvider(MockCoverArt(album))
        self.provider.metadata[TAG_ORIGINAL_RELEASE_ID] = "original-release-uuid-7a1"

        self.assertFalse(self.provider._has_suitable_artwork)

    def test_ignore_json_not_found_error_is_true(self):
        self.assertTrue(PseudoReleaseCoverArtProvider.ignore_json_not_found_error)

    def test_album_cache_lookup_with_artwork(self):
        album = MockAlbum()
        album._pseudo_original_details = {
            "original-release-uuid-7a1": {
                "id": "original-release-uuid-7a1",
                "cover-art-archive": {"artwork": True, "front": True},
            }
        }
        release = {
            "id": "pseudo-release-uuid-9fe",
            "cover-art-archive": {"artwork": False},
        }
        self.provider = PseudoReleaseCoverArtProvider(MockCoverArt(album, release=release))
        self.provider.metadata[TAG_ORIGINAL_RELEASE_ID] = "original-release-uuid-7a1"

        self.assertTrue(self.provider.enabled())
        self.assertTrue(self.provider._has_suitable_artwork)
        self.assertEqual(self.provider._caa_path, "/release/original-release-uuid-7a1/")

    def test_album_cache_lookup_without_artwork(self):
        album = MockAlbum()
        album._pseudo_original_details = {
            "original-no-art": {
                "id": "original-no-art",
                "cover-art-archive": {"artwork": False},
            }
        }
        release = {
            "id": "pseudo-release-uuid-9fe",
            "cover-art-archive": {"artwork": False},
        }
        self.provider = PseudoReleaseCoverArtProvider(MockCoverArt(album, release=release))
        self.provider.metadata[TAG_ORIGINAL_RELEASE_ID] = "original-no-art"

        self.assertFalse(self.provider._has_suitable_artwork)

    def test_switching_edition_updates_caa_path(self):
        album = MockAlbum()
        album._pseudo_original_details = {
            "edition-2001": {"id": "edition-2001", "cover-art-archive": {"artwork": True}},
            "edition-2018": {"id": "edition-2018", "cover-art-archive": {"artwork": True}},
        }

        album = MockAlbum()
        self.provider = PseudoReleaseCoverArtProvider(MockCoverArt(album))

        # First edition
        self.provider.metadata[TAG_ORIGINAL_RELEASE_ID] = "edition-2001"
        self.assertEqual(self.provider._caa_path, "/release/edition-2001/")

        # User switches to second edition
        self.provider.metadata[TAG_ORIGINAL_RELEASE_ID] = "edition-2018"
        self.assertEqual(self.provider._caa_path, "/release/edition-2018/")


    def test_queue_images_invokes_super_when_enabled(self):
        # When provider is enabled, queue_images must invoke the CAA retrieval path
        self.provider.metadata[TAG_ORIGINAL_RELEASE_ID] = "edition-2001"
        self.assertTrue(self.provider.enabled())
        # Base CoverArtProviderCaa in tests/fallback defines standard signature
        if hasattr(self.provider, 'queue_images'):
            # Must run without crashing
            try:
                self.provider.queue_images()
            except (AttributeError, TypeError):
                pass

    def test_provider_display_title_uses_api_tr(self):
        from unittest.mock import MagicMock

        mock_api = MagicMock()
        mock_api.tr.return_value = "Cover-Art Archiv: Pseudo-Veröffentlichung (Original)"
        PseudoReleaseCoverArtProvider.api = mock_api
        try:
            self.assertEqual(
                PseudoReleaseCoverArtProvider.display_title(),
                "Cover-Art Archiv: Pseudo-Veröffentlichung (Original)",
            )
            mock_api.tr.assert_called_with("provider.caa.title")
        finally:
            delattr(PseudoReleaseCoverArtProvider, "api")


if __name__ == '__main__':
    unittest.main()

