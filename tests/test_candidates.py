# Tests for candidate discovery, scoring, and ranking using real WS/2 fixtures
import json
from pathlib import Path
import unittest

from picard.metadata import Metadata
from pseudo_releases.candidates import (
    find_related_releases,
    score_original_candidate,
    select_best_original_candidate,
)
from tests.mocks.mock_picard import MockFile

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def load_fixture(mbid: str) -> dict:
    with open(FIXTURES_DIR / f"{mbid}.json", encoding="utf-8") as f:
        return json.load(f)


class TestCandidateDiscovery(unittest.TestCase):
    def setUp(self):
        self.spirited_away_orig = load_fixture("7a16f215-079e-4c55-abda-06f9a4228b6a")
        self.spirited_away_pseudo = load_fixture("9fe92739-5bcd-4f6e-b2f2-d2db97cabc32")
        self.minimoni_orig = load_fixture("1268ebdb-2fa4-423f-95da-ed7accfbb845")
        self.minimoni_pseudo_en = load_fixture("ea59c77e-1c73-4958-88fb-d86e89fb3018")

    def test_find_forward_related_releases_on_real_original_fixture(self):
        forward_related = find_related_releases(self.spirited_away_orig, direction="forward")
        self.assertEqual(len(forward_related), 3)
        ids = [r["id"] for r in forward_related]
        self.assertEqual(
            ids,
            [
                "7327ef89-e214-4f90-8d5d-3e56ffe21d0b",
                "9fe92739-5bcd-4f6e-b2f2-d2db97cabc32",
                "8b7601b3-b021-4fd3-b90f-0c5fbda16d8d",
            ],
        )
        self.assertEqual(find_related_releases(self.spirited_away_orig, direction="backward"), [])

    def test_find_backward_related_releases_on_real_pseudo_fixtures(self):
        backward_spirited = find_related_releases(self.spirited_away_pseudo, direction="backward")
        self.assertEqual(len(backward_spirited), 1)
        self.assertEqual(backward_spirited[0]["id"], "7a16f215-079e-4c55-abda-06f9a4228b6a")
        self.assertEqual(find_related_releases(self.spirited_away_pseudo, direction="forward"), [])

        backward_minimoni = find_related_releases(self.minimoni_pseudo_en, direction="backward")
        self.assertEqual(len(backward_minimoni), 1)
        self.assertEqual(backward_minimoni[0]["id"], "1268ebdb-2fa4-423f-95da-ed7accfbb845")

    def test_find_all_related_releases_ignores_non_transl_tracklisting(self):
        node = dict(self.spirited_away_pseudo)
        node["relations"] = list(self.spirited_away_pseudo["relations"]) + [
            {
                "type": "remaster",
                "type-id": "48e327b5-2d04-4518-93f1-fed5f0f0fa3c",
                "direction": "backward",
                "target-type": "release",
                "release": {"id": "unrelated-remaster-uuid", "title": "Remastered Edition"},
            }
        ]
        related = find_related_releases(node)
        self.assertEqual([r["id"] for r in related], ["7a16f215-079e-4c55-abda-06f9a4228b6a"])


class TestOriginalCandidateScoring(unittest.TestCase):
    def test_file_scoring_uses_original_multivalued_metadata(self):
        file = MockFile({"catalognumber": "supplemented value"})
        file.orig_metadata = Metadata({"catalognumber": ["TKCA-72160", "TKCA-72165"]})
        orig_node = load_fixture("7a16f215-079e-4c55-abda-06f9a4228b6a")

        score_with_cat = score_original_candidate(orig_node, files=[file])
        score_without_cat = score_original_candidate(orig_node, files=[MockFile()])

        self.assertEqual(score_with_cat - score_without_cat, 15.0)

    def test_placeholder_catalog_number_does_not_match(self):
        candidate = {"label-info": [{"catalog-number": "[none]"}]}
        file = MockFile({"catalognumber": "[none]"})

        self.assertEqual(score_original_candidate(candidate, files=[file]), 0.0)

    def test_disc_id_match_priority_with_real_fixture(self):
        spirited_away_cd = load_fixture("7a16f215-079e-4c55-abda-06f9a4228b6a")
        vinyl_reissue = {
            "id": "fd2c1b0e-9e6a-45c7-98b0-8c1e34567890",
            "title": "千と千尋の神隠し サウンドトラック",
            "status": "Official",
            "country": "JP",
            "date": "2020-11-03",
            "media": [{"format": '12" Vinyl', "track-count": 21, "discs": []}],
        }

        best = select_best_original_candidate(
            candidates=[vinyl_reissue, spirited_away_cd],
            disc_ids=["Cu4f6pXi32IYatdVVDORdGMffuA-"],
        )
        self.assertIsNotNone(best)
        self.assertEqual(best["id"], "7a16f215-079e-4c55-abda-06f9a4228b6a")

    def test_barcode_and_format_matching_with_real_fixture(self):
        spirited_away_cd = load_fixture("7a16f215-079e-4c55-abda-06f9a4228b6a")
        digital_edition = {
            "id": "a1b2c3d4-e5f6-4789-8012-3456789abcde",
            "title": "千と千尋の神隠し サウンドトラック",
            "barcode": None,
            "media": [{"format": "Digital Media", "track-count": 21}],
            "status": "Official",
            "country": "XW",
        }

        files = [MockFile({"barcode": "4988008604535", "media": "CD"})] * 21

        best = select_best_original_candidate(
            candidates=[digital_edition, spirited_away_cd],
            files=files,
        )
        self.assertIsNotNone(best)
        self.assertEqual(best["id"], "7a16f215-079e-4c55-abda-06f9a4228b6a")

    def test_medium_track_count_layout_matching(self):
        minimoni_cd = load_fixture("1268ebdb-2fa4-423f-95da-ed7accfbb845")  # 16 tracks
        spirited_cd = load_fixture("7a16f215-079e-4c55-abda-06f9a4228b6a")  # 21 tracks

        files_16 = [MockFile()] * 16
        score_16 = score_original_candidate(minimoni_cd, files=files_16)
        score_21 = score_original_candidate(spirited_cd, files=files_16)

        self.assertGreater(score_16, score_21)


if __name__ == "__main__":
    unittest.main()
