# Real-world verification tests using captured MusicBrainz API JSON fixtures
import json
from pathlib import Path
import unittest

from candidates import (
    find_related_releases,
    select_best_original_candidate,
    select_best_pseudo_candidate,
)
from constants import (
    SCRIPT_MODE_ENG,
    SCRIPT_MODE_LATN,
    TAG_ORIGINAL_RELEASE_ID,
    TAG_PSEUDO_RELEASE_ID,
)
from metadata_engine import (
    overlay_pseudo_metadata_on_album,
    supplement_pseudo_metadata,
)

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


class MockTrack:
    def __init__(self, title, artist, rec_id, discnumber="1", tracknumber="1"):
        self.metadata = MockMetadata(
            {
                "title": title,
                "artist": artist,
                "musicbrainz_recordingid": rec_id,
                "discnumber": discnumber,
                "tracknumber": tracknumber,
            }
        )
        self.orig_metadata = MockMetadata()
        self.orig_metadata.copy(self.metadata)
        self.linked_files = []

    def update_file_metadata(self, file):
        pass


class MockAlbum:
    def __init__(self, title, artist, tracks=None, initial_tags=None):
        self.metadata = MockMetadata(
            {
                "album": title,
                "albumartist": artist,
            }
        )
        if initial_tags:
            for k, v in initial_tags.items():
                self.metadata[k] = v
        self.tracks = tracks or []


class TestRealWorldFixtures(unittest.TestCase):
    def test_spirited_away_pseudo_supplementation(self):
        """Case 1 (Goal 1): Supplement Spirited Away Romaji pseudo-release
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

    def test_minimoni_disambiguation_and_overlay(self):
        """Case 2 (Bonus Goal): Minimoni 2 has 2 forward pseudo-releases (Romaji & English).
        Test script scoring disambiguation and full track overlay.
        """
        orig_node = load_fixture("1268ebdb-2fa4-423f-95da-ed7accfbb845")
        romaji_node = load_fixture("8cf6a66d-bf9c-4a29-915e-cd2791933a8d")
        english_node = load_fixture("ea59c77e-1c73-4958-88fb-d86e89fb3018")

        forward_rels = find_related_releases(orig_node, direction="forward")
        self.assertEqual(len(forward_rels), 2)

        # In Latin/Romaji mode, selects 'mini-moni. SONGUSU 2'
        best_latn = select_best_pseudo_candidate(forward_rels, target_mode=SCRIPT_MODE_LATN)
        self.assertIsNotNone(best_latn)
        self.assertEqual(best_latn["id"], "8cf6a66d-bf9c-4a29-915e-cd2791933a8d")

        # In English mode, selects 'Mini-Moni. Songs 2'
        best_eng = select_best_pseudo_candidate(forward_rels, target_mode=SCRIPT_MODE_ENG)
        self.assertIsNotNone(best_eng)
        self.assertEqual(best_eng["id"], "ea59c77e-1c73-4958-88fb-d86e89fb3018")

        # Build original tracks from the original release node
        orig_tracks = []
        for medium in orig_node["media"]:
            for trk in medium["tracks"]:
                orig_tracks.append(
                    MockTrack(
                        title=trk["title"],
                        artist=orig_node["artist-credit"][0]["name"],
                        rec_id=trk["recording"]["id"],
                        discnumber=str(medium["position"]),
                        tracknumber=str(trk["position"]),
                    )
                )

        album = MockAlbum(
            title=orig_node["title"],
            artist="ミニモニ。",
            tracks=orig_tracks,
            initial_tags={
                "barcode": orig_node["barcode"],
                "date": orig_node["date"],
                "releasecountry": orig_node["country"],
            },
        )

        # Apply Romaji overlay
        overlay_pseudo_metadata_on_album(album, romaji_node)

        # Assert album title is transliterated
        self.assertEqual(album.metadata["album"], "mini-moni. SONGUSU 2")
        self.assertEqual(album.metadata["~original_album"], "ミニモニ。ソングス2")
        self.assertEqual(album.metadata[TAG_PSEUDO_RELEASE_ID], "8cf6a66d-bf9c-4a29-915e-cd2791933a8d")

        # Assert barcode and date from original release are intact
        self.assertEqual(album.metadata["barcode"], "4942463526528")
        self.assertEqual(album.metadata["date"], "2004-02-11")
        self.assertEqual(album.metadata["releasecountry"], "JP")

        # Verify track titles are transliterated across all 16 tracks
        self.assertEqual(len(album.tracks), 16)
        # Track 1: -OPENING-
        self.assertEqual(album.tracks[0].metadata["title"], "-OPENING-")
        # Track 2: CRAZY ABOUT YOU
        self.assertEqual(album.tracks[1].metadata["title"], "CRAZY ABOUT YOU")

        # Now apply English overlay to verify switching
        overlay_pseudo_metadata_on_album(album, english_node)
        self.assertEqual(album.metadata["album"], "Mini-Moni. Songs 2")
        self.assertEqual(album.tracks[0].metadata["title"], "-Opening-")
        self.assertEqual(album.tracks[1].metadata["title"], "Crazy About You")



if __name__ == '__main__':
    unittest.main()
