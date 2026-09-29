# Tests for pseudo-release overlay on original release (Bonus Goal)
import unittest
from metadata_engine import overlay_pseudo_metadata_on_album
from constants import (
    TAG_ORIGINAL_ALBUM_ARTIST,
    TAG_ORIGINAL_ALBUM_TITLE,
    TAG_PSEUDO_RELEASE_ID,
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
    def __init__(self, album_title, album_artist, tracks, initial_tags=None):
        self.metadata = MockMetadata(
            {
                "album": album_title,
                "albumartist": album_artist,
            }
        )
        if initial_tags:
            for k, v in initial_tags.items():
                self.metadata[k] = v
        self.tracks = tracks


class TestPseudoReleaseOverlay(unittest.TestCase):
    def test_overlay_titles_and_join_phrases(self):
        # Original release in Japanese Kanji
        rec_id_1 = "rec-uuid-1"
        rec_id_2 = "rec-uuid-2"

        orig_tracks = [
            MockTrack(
                title="あの夏へ",
                artist="久石譲",
                rec_id=rec_id_1,
                discnumber="1",
                tracknumber="1",
            ),
            MockTrack(
                title="いつも何度でも",
                artist="木村弓 と 久石譲",
                rec_id=rec_id_2,
                discnumber="1",
                tracknumber="2",
            ),
        ]

        album = MockAlbum(
            album_title="千と千尋の神隠し サウンドトラック",
            album_artist="久石譲",
            tracks=orig_tracks,
            initial_tags={
                "barcode": "4988008610134",
                "date": "2001-07-18",
                "releasecountry": "JP",
            },
        )

        # Linked pseudo-release in Romaji / English with translated join phrase
        pseudo_node = {
            "id": "pseudo-release-uuid-9fe",
            "title": "Sen to Chihiro no Kamikakushi Soundtrack",
            "artist-credit": [
                {
                    "name": "Joe Hisaishi",
                    "joinphrase": "",
                    "artist": {
                        "name": "Joe Hisaishi",
                        "sort-name": "Hisaishi, Joe",
                    },
                }
            ],
            "media": [
                {
                    "position": 1,
                    "tracks": [
                        {
                            "position": 1,
                            "title": "One Summer's Day",
                            "recording": {"id": rec_id_1},
                            "artist-credit": [
                                {
                                    "name": "Joe Hisaishi",
                                    "joinphrase": "",
                                    "artist": {"name": "Joe Hisaishi", "sort-name": "Hisaishi, Joe"},
                                }
                            ],
                        },
                        {
                            "position": 2,
                            "title": "Always With Me",
                            "recording": {"id": rec_id_2},
                            "artist-credit": [
                                {
                                    "name": "Yumi Kimura",
                                    "joinphrase": " feat. ",
                                    "artist": {"name": "Yumi Kimura", "sort-name": "Kimura, Yumi"},
                                },
                                {
                                    "name": "Joe Hisaishi",
                                    "joinphrase": "",
                                    "artist": {"name": "Joe Hisaishi", "sort-name": "Hisaishi, Joe"},
                                },
                            ],
                        },
                    ],
                }
            ],
        }

        overlay_pseudo_metadata_on_album(album, pseudo_node)

        # Verify original values are preserved in ~original_* tags
        self.assertEqual(album.metadata[TAG_ORIGINAL_ALBUM_TITLE], "千と千尋の神隠し サウンドトラック")
        self.assertEqual(album.metadata[TAG_ORIGINAL_ALBUM_ARTIST], "久石譲")
        self.assertEqual(album.metadata[TAG_PSEUDO_RELEASE_ID], "pseudo-release-uuid-9fe")

        # Verify physical metadata remains intact
        self.assertEqual(album.metadata["barcode"], "4988008610134")
        self.assertEqual(album.metadata["date"], "2001-07-18")
        self.assertEqual(album.metadata["releasecountry"], "JP")

        # Verify Album Title & Artist replaced with translated values
        self.assertEqual(album.metadata["album"], "Sen to Chihiro no Kamikakushi Soundtrack")
        self.assertEqual(album.metadata["albumartist"], "Joe Hisaishi")
        self.assertEqual(album.metadata["albumartistsort"], "Hisaishi, Joe")

        # Verify Track 1 overlay
        t1 = album.tracks[0]
        self.assertEqual(t1.metadata["title"], "One Summer's Day")
        self.assertEqual(t1.metadata["artist"], "Joe Hisaishi")

        # Verify Track 2 overlay with translated join phrase (" feat. ")
        t2 = album.tracks[1]
        self.assertEqual(t2.metadata["title"], "Always With Me")
        self.assertEqual(t2.metadata["artist"], "Yumi Kimura feat. Joe Hisaishi")
        self.assertEqual(t2.metadata["artistsort"], "Kimura, Yumi feat. Hisaishi, Joe")
        self.assertEqual(t2.metadata.getall("artists"), ["Yumi Kimura", "Joe Hisaishi"])


if __name__ == '__main__':
    unittest.main()
