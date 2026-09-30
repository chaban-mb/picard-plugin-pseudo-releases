# Real-world verification tests using captured MusicBrainz API JSON fixtures
import json
from pathlib import Path
import unittest

from candidates import (
    find_related_releases,
    select_best_original_candidate,
)
from constants import TAG_ORIGINAL_RELEASE_ID
from metadata_engine import supplement_pseudo_metadata

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def load_fixture(mbid: str) -> dict:
    fixture_path = FIXTURES_DIR / f"{mbid}.json"
    with open(fixture_path, encoding="utf-8") as f:
        return json.load(f)


class MockMetadata:
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

    def copy(self, other):
        self._data = {k: list(v) for k, v in other._data.items()}


class TestRealWorldFixtures(unittest.TestCase):
    def test_spirited_away_pseudo_supplementation(self):
        """Case 1: Supplement Spirited Away Romaji pseudo-release
        with catalog metadata from original Japanese release.
        """
        pseudo_node = load_fixture("9fe92739-5bcd-4f6e-b2f2-d2db97cabc32")
        orig_node = load_fixture("7a16f215-079e-4c55-abda-06f9a4228b6a")

        # 1. Verify candidate relationship resolution
        backward_rels = find_related_releases(pseudo_node, direction="backward")
        self.assertTrue(len(backward_rels) > 0)
        best_orig = select_best_original_candidate(backward_rels)
        self.assertIsNotNone(best_orig)
        self.assertEqual(best_orig["id"], "7a16f215-079e-4c55-abda-06f9a4228b6a")

        # 2. Simulate loaded pseudo-release album metadata
        pseudo_meta = MockMetadata(
            {
                "album": pseudo_node["title"],
                "releasestatus": "pseudo-release",
            }
        )

        # 3. Apply supplementation
        supplement_pseudo_metadata(pseudo_meta, orig_node)

        # Assert physical catalog metadata is enriched from original
        self.assertEqual(pseudo_meta["date"], "2001-07-18")
        self.assertEqual(pseudo_meta["originaldate"], "2001-07-18")
        self.assertEqual(pseudo_meta["releasecountry"], "JP")
        self.assertEqual(pseudo_meta["barcode"], "4988008604535")
        self.assertEqual(pseudo_meta["media"], "CD")
        self.assertEqual(pseudo_meta.getall("catalognumber"), ["TKCA-72165"])
        self.assertEqual(pseudo_meta[TAG_ORIGINAL_RELEASE_ID], "7a16f215-079e-4c55-abda-06f9a4228b6a")

        # Assert pseudo-release title was not overwritten
        self.assertEqual(pseudo_meta["album"], "Sen to Chihiro no Kamikakushi")

if __name__ == '__main__':
    unittest.main()
