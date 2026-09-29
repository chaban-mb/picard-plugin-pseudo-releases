# Tests for artist credit and join phrase parsing
import unittest
from metadata_engine import parse_artist_credit_node


class TestArtistCreditParsing(unittest.TestCase):
    def test_single_artist(self):
        credit_list = [
            {
                "name": "Joe Hisaishi",
                "joinphrase": "",
                "artist": {
                    "id": "1",
                    "name": "Joe Hisaishi",
                    "sort-name": "Hisaishi, Joe",
                },
            }
        ]
        display, sort, names = parse_artist_credit_node(credit_list)
        self.assertEqual(display, "Joe Hisaishi")
        self.assertEqual(sort, "Hisaishi, Joe")
        self.assertEqual(names, ["Joe Hisaishi"])

    def test_dual_artists_with_feat(self):
        credit_list = [
            {
                "name": "Hiroyuki Sawano",
                "joinphrase": " feat. ",
                "artist": {
                    "id": "1",
                    "name": "Hiroyuki Sawano",
                    "sort-name": "Sawano, Hiroyuki",
                },
            },
            {
                "name": "Mika Kobayashi",
                "joinphrase": "",
                "artist": {
                    "id": "2",
                    "name": "Mika Kobayashi",
                    "sort-name": "Kobayashi, Mika",
                },
            },
        ]
        display, sort, names = parse_artist_credit_node(credit_list)
        self.assertEqual(display, "Hiroyuki Sawano feat. Mika Kobayashi")
        self.assertEqual(sort, "Sawano, Hiroyuki feat. Kobayashi, Mika")
        self.assertEqual(names, ["Hiroyuki Sawano", "Mika Kobayashi"])

    def test_three_artists_with_comma_and_ampersand(self):
        credit_list = [
            {
                "name": "Artist A",
                "joinphrase": ", ",
                "artist": {"name": "Artist A", "sort-name": "A, Artist"},
            },
            {
                "name": "Artist B",
                "joinphrase": " & ",
                "artist": {"name": "Artist B", "sort-name": "B, Artist"},
            },
            {
                "name": "Artist C",
                "joinphrase": "",
                "artist": {"name": "Artist C", "sort-name": "C, Artist"},
            },
        ]
        display, sort, names = parse_artist_credit_node(credit_list)
        self.assertEqual(display, "Artist A, Artist B & Artist C")
        self.assertEqual(sort, "A, Artist, B, Artist & C, Artist")
        self.assertEqual(names, ["Artist A", "Artist B", "Artist C"])

    def test_japanese_join_phrase(self):
        credit_list = [
            {
                "name": "初音ミク",
                "joinphrase": " と ",
                "artist": {"name": "初音ミク", "sort-name": "Hatsune, Miku"},
            },
            {
                "name": "鏡音リン",
                "joinphrase": "",
                "artist": {"name": "鏡音リン", "sort-name": "Kagamine, Rin"},
            },
        ]
        display, sort, names = parse_artist_credit_node(credit_list)
        self.assertEqual(display, "初音ミク と 鏡音リン")
        self.assertEqual(sort, "Hatsune, Miku と Kagamine, Rin")
        self.assertEqual(names, ["初音ミク", "鏡音リン"])

    def test_fallback_when_name_missing_in_credit_node(self):
        credit_list = [
            {
                "name": "",
                "joinphrase": "",
                "artist": {
                    "name": "Fallback Artist",
                    "sort-name": "Artist, Fallback",
                },
            }
        ]
        display, sort, names = parse_artist_credit_node(credit_list)
        self.assertEqual(display, "Fallback Artist")
        self.assertEqual(sort, "Artist, Fallback")
        self.assertEqual(names, ["Fallback Artist"])

    def test_empty_credit_list(self):
        display, sort, names = parse_artist_credit_node([])
        self.assertEqual(display, "")
        self.assertEqual(sort, "")
        self.assertEqual(names, [])

        display_none, sort_none, names_none = parse_artist_credit_node(None)
        self.assertEqual(display_none, "")
        self.assertEqual(sort_none, "")
        self.assertEqual(names_none, [])


if __name__ == '__main__':
    unittest.main()
