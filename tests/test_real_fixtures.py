# Real-world verification tests using captured MusicBrainz API JSON fixtures
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

import pseudo_releases as plugin_module
from pseudo_releases.caa_provider import PseudoReleaseCoverArtProvider
from pseudo_releases.constants import TAG_ORIGINAL_RELEASE_ID
from tests.mocks.mock_picard import (
    MockAlbum,
    MockPluginApi,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def load_fixture(mbid: str) -> dict:
    fixture_path = FIXTURES_DIR / f"{mbid}.json"
    with open(fixture_path, encoding="utf-8") as f:
        return json.load(f)


class TestRealWorldFixtures(unittest.TestCase):
    def setUp(self):
        self.api = MockPluginApi()
        plugin_module.enable(self.api)

    def test_spirited_away_romaji_default_end_to_end(self):
        """Case 1: Spirited Away Romaji pseudo-release (9fe92739)
        supplemented with catalog metadata from original Japanese release (7a16f215).
        """
        pseudo_node = load_fixture("9fe92739-5bcd-4f6e-b2f2-d2db97cabc32")
        orig_node = load_fixture("7a16f215-079e-4c55-abda-06f9a4228b6a")

        pseudo_album = MockAlbum(
            album_id=pseudo_node["id"],
            title=pseudo_node["title"],
            status="Pseudo-Release",
            release_node=pseudo_node,
        )

        def mock_get_release(rel_id, callback, inc=None, **kwargs):
            self.assertEqual(rel_id, "7a16f215-079e-4c55-abda-06f9a4228b6a")
            callback(orig_node, None, None)

        self.api.mb_api.get_release_by_id.side_effect = mock_get_release

        # Trigger metadata processor
        plugin_module.PseudoReleasePlugin.process_album_metadata(
            api=self.api,
            album=pseudo_album,
            album_metadata=pseudo_album.metadata,
            release_node=pseudo_node,
        )

        # 1. Assert task execution
        self.assertTrue(
            any(
                task[1] == "pseudo_enrich_7a16f215-079e-4c55-abda-06f9a4228b6a"
                for task in self.api.completed_tasks
            )
        )
        self.assertTrue(pseudo_album._finalized)

        # 2. Assert enriched catalog metadata and media node alignment
        meta = pseudo_album.metadata
        self.assertEqual(meta["date"], "2001-07-18")
        self.assertEqual(meta["releasecountry"], "JP")
        self.assertEqual(meta["barcode"], "4988008604535")
        self.assertEqual(meta["media"], "CD")
        self.assertEqual(pseudo_album._release_node["media"][0]["format"], "CD")
        self.assertEqual(meta.getall("catalognumber"), ["TKCA-72165"])
        self.assertEqual(meta.getall("label"), ["STUDIO GHIBLI RECORDS"])
        self.assertEqual(meta[TAG_ORIGINAL_RELEASE_ID], "7a16f215-079e-4c55-abda-06f9a4228b6a")

        # 3. Assert Romaji title was preserved
        self.assertEqual(meta["album"], "Sen to Chihiro no Kamikakushi")

        # 4. Assert CAA provider routes to original release
        mock_coverart = SimpleNamespace(
            album=pseudo_album,
            metadata=meta,
            release=pseudo_node,
            tagger=self.api.tagger,
            front_image_found=False,
        )
        caa_provider = PseudoReleaseCoverArtProvider(mock_coverart)
        self.assertTrue(caa_provider.enabled())
        self.assertEqual(caa_provider._caa_path, "/release/7a16f215-079e-4c55-abda-06f9a4228b6a/")

    def test_minimoni_english_translation_default_end_to_end(self):
        """Case 2: Minimoni Songs 2 English translated pseudo-release (ea59c77e)
        supplemented from Japanese original release (1268ebdb).
        """
        pseudo_node = load_fixture("ea59c77e-1c73-4958-88fb-d86e89fb3018")
        orig_node = load_fixture("1268ebdb-2fa4-423f-95da-ed7accfbb845")

        pseudo_album = MockAlbum(
            album_id=pseudo_node["id"],
            title=pseudo_node["title"],
            status="Pseudo-Release",
            release_node=pseudo_node,
        )

        def mock_get_release(rel_id, callback, inc=None, **kwargs):
            self.assertEqual(rel_id, "1268ebdb-2fa4-423f-95da-ed7accfbb845")
            callback(orig_node, None, None)

        self.api.mb_api.get_release_by_id.side_effect = mock_get_release

        plugin_module.PseudoReleasePlugin.process_album_metadata(
            api=self.api,
            album=pseudo_album,
            album_metadata=pseudo_album.metadata,
            release_node=pseudo_node,
        )

        meta = pseudo_album.metadata
        self.assertEqual(meta["date"], "2004-02-11")
        self.assertEqual(meta["releasecountry"], "JP")
        self.assertEqual(meta["barcode"], "4942463526528")
        self.assertEqual(meta["media"], "CD")
        self.assertEqual(pseudo_album._release_node["media"][0]["format"], "CD")
        self.assertEqual(meta.getall("catalognumber"), ["EPCE-5265"])
        self.assertEqual(meta.getall("label"), ["zetima"])
        self.assertEqual(meta[TAG_ORIGINAL_RELEASE_ID], "1268ebdb-2fa4-423f-95da-ed7accfbb845")

        # English translated title is preserved
        self.assertEqual(meta["album"], "Mini-Moni. Songs 2")

    def test_minimoni_romaji_alternative_tracklist(self):
        """Case 3: Minimoni Songs 2 Romaji pseudo-release (8cf6a66d)
        supplemented from Japanese original release (1268ebdb).
        """
        pseudo_node = load_fixture("8cf6a66d-bf9c-4a29-915e-cd2791933a8d")
        orig_node = load_fixture("1268ebdb-2fa4-423f-95da-ed7accfbb845")

        pseudo_album = MockAlbum(
            album_id=pseudo_node["id"],
            title=pseudo_node["title"],
            status="Pseudo-Release",
            release_node=pseudo_node,
        )

        def mock_get_release(rel_id, callback, inc=None, **kwargs):
            callback(orig_node, None, None)

        self.api.mb_api.get_release_by_id.side_effect = mock_get_release

        plugin_module.PseudoReleasePlugin.process_album_metadata(
            api=self.api,
            album=pseudo_album,
            album_metadata=pseudo_album.metadata,
            release_node=pseudo_node,
        )

        meta = pseudo_album.metadata
        self.assertEqual(meta["barcode"], "4942463526528")
        self.assertEqual(meta[TAG_ORIGINAL_RELEASE_ID], "1268ebdb-2fa4-423f-95da-ed7accfbb845")
        self.assertEqual(meta["album"], "mini-moni. SONGUSU 2")
        self.assertEqual(pseudo_album._release_node["media"][0]["format"], "CD")

    def test_real_release_context_menu_options(self):
        """Test: Linked original editions action shows and formats candidates correctly."""
        pseudo_node = load_fixture("9fe92739-5bcd-4f6e-b2f2-d2db97cabc32")
        orig_node = load_fixture("7a16f215-079e-4c55-abda-06f9a4228b6a")

        pseudo_album = MockAlbum(
            album_id=pseudo_node["id"],
            title=pseudo_node["title"],
            status="Pseudo-Release",
            release_node=pseudo_node,
        )
        pseudo_album._pseudo_original_candidates = [orig_node]
        self.api.tagger.window.selected_objects = [pseudo_album]

        action_enabled = plugin_module.ChooseLinkedOriginalAction()
        self.assertTrue(action_enabled.isEnabled())

        # Candidate label formatting verification on Spirited Away (7a16f215)
        formatted_label = plugin_module.PseudoReleasePlugin._format_original_candidate(orig_node)
        self.assertEqual(
            formatted_label,
            "21 / 2001 / JP / CD / STUDIO GHIBLI RECORDS / TKCA-72165",
        )

        # Tooltip formatting verification
        tooltip = plugin_module.PseudoReleasePlugin._format_original_candidate_tooltip(orig_node)
        self.assertIn("4988008604535", tooltip)
        self.assertIn("Middle-click or right-click to open in browser.", tooltip)

        # Catalog number deduplication test with Minimoni candidate (1268ebdb has duplicate EPCE-5265)
        minimoni_orig = load_fixture("1268ebdb-2fa4-423f-95da-ed7accfbb845")
        minimoni_label = plugin_module.PseudoReleasePlugin._format_original_candidate(minimoni_orig)
        self.assertEqual(minimoni_label.count("EPCE-5265"), 1)
        self.assertEqual(minimoni_label, "16 / 2004 / JP / CD / zetima / EPCE-5265")
        minimoni_tooltip = plugin_module.PseudoReleasePlugin._format_original_candidate_tooltip(
            minimoni_orig
        )
        self.assertIn("Jewel Case", minimoni_tooltip)
        self.assertIn("4942463526528", minimoni_tooltip)

        # ReleaseGroup header reuse verification
        self.assertEqual(
            action_enabled.menu().actions()[0].text(),
            "Tracks / Year / Country / Format / Label / Cat No",
        )
        pseudo_album.release_group = SimpleNamespace(
            version_headings="Titel / Jahr / Land / Format / Label / Kat.-Nr."
        )
        action_with_rg = plugin_module.ChooseLinkedOriginalAction()
        self.assertEqual(
            action_with_rg.menu().actions()[0].text(),
            "Titel / Jahr / Land / Format / Label / Kat.-Nr.",
        )

        # >10 media truncation test: Picard's VERSIONS_MAX_TRACKS truncation with +…
        boxset_cand = {
            "id": "boxset-cand",
            "date": "2022-03-15",
            "country": "GB",
            "media": [{"format": "CD", "track-count": 10}] * 12,
        }
        boxset_label = plugin_module.PseudoReleasePlugin._format_original_candidate(boxset_cand)
        self.assertIn("+".join(["10"] * 10) + "+…", boxset_label)
        self.assertIn("12×CD", boxset_label)


if __name__ == "__main__":
    unittest.main()
