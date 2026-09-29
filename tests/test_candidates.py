# Tests for candidate discovery, scoring, and ranking
import unittest
from candidates import (
    find_related_releases,
    score_original_candidate,
    score_pseudo_candidate,
    select_best_original_candidate,
    select_best_pseudo_candidate,
)
from constants import (
    SCRIPT_MODE_ENG,
    SCRIPT_MODE_LATN,
    SCRIPT_MODE_LOCALES,
)


class MockFile:
    def __init__(self, metadata=None):
        self.metadata = metadata or {}


class TestCandidateDiscovery(unittest.TestCase):
    def setUp(self):
        self.relations_fixture = {
            "relations": [
                {
                    "type": "transl-tracklisting",
                    "type-id": "fc399d47-23a7-4c28-bfcf-0607a562b644",
                    "direction": "forward",
                    "release": {
                        "id": "pseudo-romaji-id",
                        "title": "Sen to Chihiro no Kamikakushi",
                        "status": "Pseudo-Release",
                        "text-representation": {"script": "Latn", "language": "jpn"},
                        "disambiguation": "English transliteration",
                    },
                },
                {
                    "type": "transl-tracklisting",
                    "type-id": "fc399d47-23a7-4c28-bfcf-0607a562b644",
                    "direction": "forward",
                    "release": {
                        "id": "pseudo-english-id",
                        "title": "Spirited Away",
                        "status": "Pseudo-Release",
                        "text-representation": {"script": "Latn", "language": "eng"},
                        "disambiguation": "English translation",
                    },
                },
                {
                    "type": "transl-tracklisting",
                    "type-id": "fc399d47-23a7-4c28-bfcf-0607a562b644",
                    "direction": "backward",
                    "release": {
                        "id": "original-release-id",
                        "title": "千と千尋の神隠し",
                        "status": "Official",
                        "date": "2001-07-18",
                    },
                },
                {
                    "type": "part-of",
                    "direction": "forward",
                    "release": {"id": "other-rel-id", "title": "Other"},
                },
            ]
        }

    def test_find_all_related_releases(self):
        all_related = find_related_releases(self.relations_fixture)
        self.assertEqual(len(all_related), 3)
        ids = [r["id"] for r in all_related]
        self.assertIn("pseudo-romaji-id", ids)
        self.assertIn("pseudo-english-id", ids)
        self.assertIn("original-release-id", ids)
        self.assertNotIn("other-rel-id", ids)

    def test_find_forward_related_releases(self):
        forward_related = find_related_releases(self.relations_fixture, direction="forward")
        self.assertEqual(len(forward_related), 2)
        ids = [r["id"] for r in forward_related]
        self.assertIn("pseudo-romaji-id", ids)
        self.assertIn("pseudo-english-id", ids)
        self.assertNotIn("original-release-id", ids)

    def test_find_backward_related_releases(self):
        backward_related = find_related_releases(self.relations_fixture, direction="backward")
        self.assertEqual(len(backward_related), 1)
        self.assertEqual(backward_related[0]["id"], "original-release-id")


class TestOriginalCandidateScoring(unittest.TestCase):
    def test_disc_id_match_priority(self):
        candidate_cd = {
            "id": "cd-cand-id",
            "title": "Original CD",
            "status": "Official",
            "media": [
                {
                    "format": "CD",
                    "discs": [{"id": "disc-toc-match-123"}],
                    "track-count": 10,
                }
            ],
        }
        candidate_vinyl = {
            "id": "vinyl-cand-id",
            "title": "Original Vinyl",
            "status": "Official",
            "media": [
                {
                    "format": "12\" Vinyl",
                    "track-count": 10,
                }
            ],
        }

        # Loaded CD with matching disc ID
        best = select_best_original_candidate(
            candidates=[candidate_vinyl, candidate_cd],
            disc_ids=["disc-toc-match-123"],
        )
        self.assertIsNotNone(best)
        self.assertEqual(best["id"], "cd-cand-id")

    def test_barcode_and_format_matching(self):
        candidate_cd = {
            "id": "cd-cand",
            "barcode": "4988008610134",
            "media": [{"format": "CD", "track-count": 21}],
            "status": "Official",
        }
        candidate_digital = {
            "id": "digital-cand",
            "barcode": "1234567890000",
            "media": [{"format": "Digital Media", "track-count": 21}],
            "status": "Official",
        }

        # Files have barcode 4988008610134 and media tag 'CD'
        files = [
            MockFile({"barcode": "4988008610134", "media": "CD"}),
        ] * 21

        best = select_best_original_candidate(
            candidates=[candidate_digital, candidate_cd],
            files=files,
        )
        self.assertIsNotNone(best)
        self.assertEqual(best["id"], "cd-cand")

    def test_medium_track_count_layout_matching(self):
        # 1 CD edition (16 tracks total)
        candidate_cd = {
            "id": "cd-16",
            "media": [{"format": "CD", "track-count": 16}],
        }
        # 2 LP edition (8 tracks + 8 tracks = 16, vs 10 tracks edition)
        candidate_lp_10 = {
            "id": "lp-10",
            "media": [{"format": "Vinyl", "track-count": 10}],
        }

        files = [MockFile()] * 16
        score_16 = score_original_candidate(candidate_cd, files=files)
        score_10 = score_original_candidate(candidate_lp_10, files=files)

        self.assertGreater(score_16, score_10)


class TestPseudoCandidateScoring(unittest.TestCase):
    def setUp(self):
        self.cand_romaji = {
            "id": "romaji",
            "title": "Sen to Chihiro no Kamikakushi",
            "status": "Pseudo-Release",
            "text-representation": {"script": "Latn", "language": "jpn"},
            "disambiguation": "English transliteration (Hepburn romaji)",
        }
        self.cand_english = {
            "id": "english",
            "title": "Spirited Away",
            "status": "Pseudo-Release",
            "text-representation": {"script": "Latn", "language": "eng"},
            "disambiguation": "English translation",
        }
        self.cand_french = {
            "id": "french",
            "title": "Le Voyage de Chihiro",
            "status": "Pseudo-Release",
            "text-representation": {"script": "Latn", "language": "fra"},
            "disambiguation": "French translation",
        }
        self.candidates = [self.cand_english, self.cand_romaji, self.cand_french]

    def test_select_latn_romaji_mode(self):
        best = select_best_pseudo_candidate(
            self.candidates,
            target_mode=SCRIPT_MODE_LATN,
        )
        self.assertIsNotNone(best)
        self.assertEqual(best["id"], "romaji")

    def test_select_english_mode(self):
        best = select_best_pseudo_candidate(
            self.candidates,
            target_mode=SCRIPT_MODE_ENG,
        )
        self.assertIsNotNone(best)
        self.assertEqual(best["id"], "english")

    def test_select_locale_mode(self):
        best = select_best_pseudo_candidate(
            self.candidates,
            target_mode=SCRIPT_MODE_LOCALES,
            preferred_locales=["fr_FR", "en_US"],
        )
        self.assertIsNotNone(best)
        self.assertEqual(best["id"], "french")


if __name__ == '__main__':
    unittest.main()
