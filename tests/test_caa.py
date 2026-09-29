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


if __name__ == '__main__':
    unittest.main()
