# Tests for PseudoReleaseCoverArtProvider
import unittest
from caa_provider import PseudoReleaseCoverArtProvider
from constants import TAG_ORIGINAL_RELEASE_ID


class TestPseudoReleaseCoverArtProvider(unittest.TestCase):
    def setUp(self):
        self.provider = PseudoReleaseCoverArtProvider()
        self.provider.metadata = {
            "musicbrainz_albumid": "pseudo-release-uuid-9fe",
        }
        self.provider.release = {
            "id": "pseudo-release-uuid-9fe",
            "cover-art-archive": {"artwork": True},
        }

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
        self.provider.metadata[TAG_ORIGINAL_RELEASE_ID] = "original-release-uuid-7a1"
        self.provider.release["cover-art-archive"]["artwork"] = False

        self.assertFalse(self.provider._has_suitable_artwork)

    def test_ignore_json_not_found_error_is_true(self):
        self.assertTrue(PseudoReleaseCoverArtProvider.ignore_json_not_found_error)

    def test_album_cache_lookup_with_artwork(self):
        class MockCoverArt:
            def __init__(self, album):
                self.album = album
                self.front_image_found = False

        class MockAlbum:
            def __init__(self):
                self._pseudo_original_details = {
                    "original-release-uuid-7a1": {
                        "id": "original-release-uuid-7a1",
                        "cover-art-archive": {"artwork": True, "front": True},
                    }
                }

        album = MockAlbum()
        self.provider.coverart = MockCoverArt(album)
        self.provider.album = album
        # The pseudo release itself has NO artwork:
        self.provider.release = {
            "id": "pseudo-release-uuid-9fe",
            "cover-art-archive": {"artwork": False},
        }
        self.provider.metadata[TAG_ORIGINAL_RELEASE_ID] = "original-release-uuid-7a1"

        self.assertTrue(self.provider.enabled())
        self.assertTrue(self.provider._has_suitable_artwork)
        self.assertEqual(self.provider._caa_path, "/release/original-release-uuid-7a1/")

    def test_album_cache_lookup_without_artwork(self):
        class MockCoverArt:
            def __init__(self, album):
                self.album = album
                self.front_image_found = False

        class MockAlbum:
            def __init__(self):
                self._pseudo_original_details = {
                    "original-no-art": {
                        "id": "original-no-art",
                        "cover-art-archive": {"artwork": False},
                    }
                }

        album = MockAlbum()
        self.provider.coverart = MockCoverArt(album)
        self.provider.album = album
        self.provider.release = {
            "id": "pseudo-release-uuid-9fe",
            "cover-art-archive": {"artwork": False},
        }
        self.provider.metadata[TAG_ORIGINAL_RELEASE_ID] = "original-no-art"

        self.assertFalse(self.provider._has_suitable_artwork)

    def test_switching_edition_updates_caa_path(self):
        class MockCoverArt:
            def __init__(self, album):
                self.album = album
                self.front_image_found = False

        class MockAlbum:
            def __init__(self):
                self._pseudo_original_details = {
                    "edition-2001": {"id": "edition-2001", "cover-art-archive": {"artwork": True}},
                    "edition-2018": {"id": "edition-2018", "cover-art-archive": {"artwork": True}},
                }

        album = MockAlbum()
        self.provider.coverart = MockCoverArt(album)
        self.provider.album = album

        # First edition
        self.provider.metadata[TAG_ORIGINAL_RELEASE_ID] = "edition-2001"
        self.assertEqual(self.provider._caa_path, "/release/edition-2001/")

        # User switches to second edition
        self.provider.metadata[TAG_ORIGINAL_RELEASE_ID] = "edition-2018"
        self.assertEqual(self.provider._caa_path, "/release/edition-2018/")


if __name__ == '__main__':
    unittest.main()
