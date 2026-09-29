# Tests for pseudo-release metadata supplementation (Goal 1)
import unittest
from metadata_engine import (
    extract_release_catalog_metadata,
    supplement_pseudo_metadata,
)
from constants import (
    TAG_ORIGINAL_RELEASE_ID,
)


class MockMetadata:
    """Mock Picard Metadata object matching internal behavior."""

    def __init__(self, initial=None):
        self._data = {}
        if initial:
            for k, v in initial.items():
                self[k] = v

    def __setitem__(self, key, value):
        if isinstance(value, list):
            self._data[key] = [str(x) for x in value]
        else:
            self._data[key] = [str(value)]

    def __getitem__(self, key):
        if key in self._data and self._data[key]:
            return "; ".join(self._data[key])
        return ""

    def get(self, key, default=""):
        val = self[key]
        return val if val else default

    def getall(self, key):
        return list(self._data.get(key, []))


class TestMetadataSupplementation(unittest.TestCase):
    def test_extract_catalog_metadata(self):
        orig_node = {
            "id": "7a16f215-079e-4c55-abda-06f9a4228b6a",
            "title": "千と千尋の神隠し サウンドトラック",
            "date": "2001-07-18",
            "country": "JP",
            "barcode": "4988008610134",
            "media": [{"format": "CD", "track-count": 21}],
            "label-info": [
                {
                    "catalog-number": "TKCA-72165",
                    "label": {"name": "Tokuma Japan Communications"},
                }
            ],
        }

        catalog = extract_release_catalog_metadata(orig_node)
        self.assertEqual(catalog["date"], "2001-07-18")
        self.assertEqual(catalog["originaldate"], "2001-07-18")
        self.assertEqual(catalog["releasecountry"], "JP")
        self.assertEqual(catalog["barcode"], "4988008610134")
        self.assertEqual(catalog["media"], "CD")
        self.assertEqual(catalog["label"], ["Tokuma Japan Communications"])
        self.assertEqual(catalog["catalognumber"], ["TKCA-72165"])

    def test_supplement_pseudo_metadata(self):
        # A pseudo-release with translated titles but missing catalog data
        pseudo_meta = MockMetadata(
            {
                "album": "Spirited Away: Original Soundtrack",
                "albumartist": "Joe Hisaishi",
                "releasestatus": "pseudo-release",
            }
        )

        orig_node = {
            "id": "7a16f215-079e-4c55-abda-06f9a4228b6a",
            "date": "2001-07-18",
            "country": "JP",
            "barcode": "4988008610134",
            "media": [{"format": "CD"}],
            "label-info": [
                {
                    "catalog-number": "TKCA-72165",
                    "label": {"name": "Tokuma Japan Communications"},
                }
            ],
        }

        supplement_pseudo_metadata(pseudo_meta, orig_node)

        # Catalog data should be populated
        self.assertEqual(pseudo_meta["date"], "2001-07-18")
        self.assertEqual(pseudo_meta["originaldate"], "2001-07-18")
        self.assertEqual(pseudo_meta["releasecountry"], "JP")
        self.assertEqual(pseudo_meta["barcode"], "4988008610134")
        self.assertEqual(pseudo_meta["media"], "CD")
        self.assertEqual(pseudo_meta.getall("label"), ["Tokuma Japan Communications"])
        self.assertEqual(pseudo_meta.getall("catalognumber"), ["TKCA-72165"])
        self.assertEqual(pseudo_meta[TAG_ORIGINAL_RELEASE_ID], "7a16f215-079e-4c55-abda-06f9a4228b6a")

        # Titles must remain unchanged
        self.assertEqual(pseudo_meta["album"], "Spirited Away: Original Soundtrack")
        self.assertEqual(pseudo_meta["albumartist"], "Joe Hisaishi")


if __name__ == '__main__':
    unittest.main()
