# Tests for pseudo-release metadata supplementation
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from picard.metadata import Metadata
from picard.options import StandardizeArtistNames
from pseudo_releases import metadata_engine
from pseudo_releases.constants import TAG_ORIGINAL_RELEASE_ID
from pseudo_releases.metadata_engine import (
    extract_release_catalog_metadata,
    get_enrichment_inc_params,
    supplement_pseudo_media,
    supplement_pseudo_metadata,
    supplement_release_relationships_and_genres,
)
from tests.mocks.mock_picard import MockAlbum

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def load_fixture(mbid: str) -> dict:
    with open(FIXTURES_DIR / f"{mbid}.json", encoding="utf-8") as f:
        return json.load(f)


class TestMetadataSupplementation(unittest.TestCase):
    def test_extract_catalog_metadata_from_real_fixtures(self):
        spirited_away_orig = load_fixture("7a16f215-079e-4c55-abda-06f9a4228b6a")
        catalog = extract_release_catalog_metadata(spirited_away_orig)
        self.assertEqual(catalog["date"], "2001-07-18")
        self.assertNotIn("originaldate", catalog)
        self.assertEqual(catalog["releasecountry"], "JP")
        self.assertEqual(catalog["barcode"], "4988008604535")
        self.assertEqual(catalog["media"], "CD")
        self.assertEqual(catalog["label"], ["STUDIO GHIBLI RECORDS"])
        self.assertEqual(catalog["catalognumber"], ["TKCA-72165"])

        # Minimoni fixture (1268ebdb) has two label-info entries with duplicate catalog-number EPCE-5265
        minimoni_orig = load_fixture("1268ebdb-2fa4-423f-95da-ed7accfbb845")
        minimoni_catalog = extract_release_catalog_metadata(minimoni_orig)
        self.assertEqual(minimoni_catalog["date"], "2004-02-11")
        self.assertEqual(minimoni_catalog["releasecountry"], "JP")
        self.assertEqual(minimoni_catalog["barcode"], "4942463526528")
        self.assertEqual(minimoni_catalog["media"], "CD")
        self.assertEqual(minimoni_catalog["label"], ["zetima"])
        self.assertEqual(minimoni_catalog["catalognumber"], ["EPCE-5265"])

    def test_supplement_pseudo_metadata_from_real_fixture(self):
        pseudo_meta = Metadata(
            {
                "album": "Sen to Chihiro no Kamikakushi",
                "albumartist": "Joe Hisaishi",
                "releasestatus": "pseudo-release",
            }
        )
        orig_node = load_fixture("7a16f215-079e-4c55-abda-06f9a4228b6a")

        supplement_pseudo_metadata(pseudo_meta, orig_node)

        self.assertEqual(pseudo_meta["date"], "2001-07-18")
        self.assertEqual(pseudo_meta["originaldate"], "")
        self.assertEqual(pseudo_meta["releasecountry"], "JP")
        self.assertEqual(pseudo_meta["barcode"], "4988008604535")
        self.assertEqual(pseudo_meta["media"], "CD")
        self.assertEqual(pseudo_meta.getall("label"), ["STUDIO GHIBLI RECORDS"])
        self.assertEqual(pseudo_meta.getall("catalognumber"), ["TKCA-72165"])
        self.assertEqual(
            pseudo_meta[TAG_ORIGINAL_RELEASE_ID],
            "7a16f215-079e-4c55-abda-06f9a4228b6a",
        )
        self.assertEqual(pseudo_meta["album"], "Sen to Chihiro no Kamikakushi")
        self.assertEqual(pseudo_meta["albumartist"], "Joe Hisaishi")

    def test_supplement_updates_media_nodes_before_picard_loads_tracks(self):
        pseudo_node = load_fixture("9fe92739-5bcd-4f6e-b2f2-d2db97cabc32")
        orig_node = load_fixture("7a16f215-079e-4c55-abda-06f9a4228b6a")
        album = MockAlbum(
            album_id=pseudo_node["id"],
            release_node=pseudo_node,
        )
        self.assertIsNone(album._release_node["media"][0]["format"])

        supplement_pseudo_media(album, orig_node)

        self.assertEqual(album._release_node["media"][0]["format"], "CD")

    def test_supplement_overwrites_by_default_and_preserves_when_enabled(self):
        orig_node = load_fixture("7a16f215-079e-4c55-abda-06f9a4228b6a")

        meta_overwrite = Metadata(
            {
                "album": "Sen to Chihiro no Kamikakushi",
                "date": "2002-09-10",
                "releasecountry": "US",
            }
        )
        supplement_pseudo_metadata(meta_overwrite, orig_node, preserve_existing=False)
        self.assertEqual(meta_overwrite["date"], "2001-07-18")
        self.assertEqual(meta_overwrite["releasecountry"], "JP")
        self.assertEqual(meta_overwrite["barcode"], "4988008604535")

        meta_preserve = Metadata(
            {
                "album": "Sen to Chihiro no Kamikakushi",
                "date": "2002-09-10",
                "releasecountry": "US",
            }
        )
        supplement_pseudo_metadata(meta_preserve, orig_node, preserve_existing=True)
        self.assertEqual(meta_preserve["date"], "2002-09-10")
        self.assertEqual(meta_preserve["releasecountry"], "US")
        self.assertEqual(meta_preserve["barcode"], "4988008604535")

    def test_supplement_omits_original_id_tag_when_disabled(self):
        pseudo_meta = Metadata({"album": "Sen to Chihiro no Kamikakushi"})
        orig_node = load_fixture("7a16f215-079e-4c55-abda-06f9a4228b6a")

        supplement_pseudo_metadata(pseudo_meta, orig_node, set_original_id=False)

        self.assertEqual(pseudo_meta["date"], "2001-07-18")
        self.assertNotIn(TAG_ORIGINAL_RELEASE_ID, pseudo_meta)

    def test_get_enrichment_inc_params(self):
        cfg_default = SimpleNamespace(setting={"release_ars": False, "use_genres": False})
        params = get_enrichment_inc_params(cfg_default)
        self.assertIn("labels", params)
        self.assertIn("media", params)
        self.assertNotIn("artist-rels", params)
        self.assertNotIn("tags", params)

        cfg_ars = SimpleNamespace(setting={"release_ars": True, "use_genres": False})
        params_ars = get_enrichment_inc_params(cfg_ars)
        self.assertIn("artist-rels", params_ars)
        self.assertIn("url-rels", params_ars)
        self.assertIn("series-rels", params_ars)
        self.assertIn("label-rels", params_ars)
        self.assertNotIn("tags", params_ars)

        cfg_genres = SimpleNamespace(
            setting={"release_ars": False, "use_genres": True, "only_my_genres": False}
        )
        params_genres = get_enrichment_inc_params(cfg_genres)
        self.assertIn("tags", params_genres)
        self.assertIn("genres", params_genres)
        self.assertNotIn("artist-rels", params_genres)

        cfg_user_genres = SimpleNamespace(
            setting={"release_ars": False, "use_genres": True, "only_my_genres": True}
        )
        params_user_genres = get_enrichment_inc_params(cfg_user_genres)
        self.assertIn("user-tags", params_user_genres)
        self.assertIn("user-genres", params_user_genres)

    def test_supplement_relationships_and_genres_with_real_picard_mbjson(self):
        pseudo_node = load_fixture("9fe92739-5bcd-4f6e-b2f2-d2db97cabc32")
        orig_node = load_fixture("7a16f215-079e-4c55-abda-06f9a4228b6a")

        # Enrich orig_node with realistic WS/2 artist, URL (with MBID), per-medium mix-DJ, and genre/tag nodes
        orig_node["relations"].extend(
            [
                {
                    "type": "producer",
                    "type-id": "8bf377ba-8d71-4ecc-97f2-7bb2d8a2a75f",
                    "direction": "backward",
                    "target-type": "artist",
                    "attributes": [],
                    "attribute-values": {},
                    "attribute-ids": {},
                    "begin": None,
                    "end": None,
                    "ended": False,
                    "source-credit": "",
                    "target-credit": "",
                    "artist": {
                        "id": "44c64a30-1d58-49c5-b314-6e02fba49526",
                        "name": "久石譲",
                        "sort-name": "Hisaishi, Joe",
                        "disambiguation": "composer & musical director",
                    },
                },
                {
                    "type": "amazon asin",
                    "type-id": "4f2e710d-166c-480c-a293-2e2c8d658d87",
                    "direction": "forward",
                    "target-type": "url",
                    "attributes": [],
                    "attribute-values": {},
                    "attribute-ids": {},
                    "begin": None,
                    "end": None,
                    "ended": False,
                    "source-credit": "",
                    "target-credit": "",
                    "url": {
                        "id": "b1f29a88-5e2b-49b7-9359-2785850c94d7",
                        "resource": "https://www.amazon.co.jp/dp/B00005L8N4",
                    },
                },
                {
                    "type": "mix-DJ",
                    "type-id": "28338ee6-d578-485a-bb53-61dbfd7c6545",
                    "direction": "backward",
                    "target-type": "artist",
                    "attributes": ["medium 1"],
                    "attribute-values": {},
                    "attribute-ids": {"medium 1": "39ee6d4b-f02e-4f01-9625-282c81f53683"},
                    "begin": None,
                    "end": None,
                    "ended": False,
                    "source-credit": "",
                    "target-credit": "",
                    "artist": {
                        "id": "44c64a30-1d58-49c5-b314-6e02fba49526",
                        "name": "久石譲",
                        "sort-name": "Hisaishi, Joe",
                    },
                },
            ]
        )
        orig_node["tags"] = [{"name": "studio ghibli", "count": 5}]
        orig_node["genres"] = [{"name": "anime", "count": 3}]

        album = MockAlbum(
            album_id=pseudo_node["id"],
            title=pseudo_node["title"],
            status="Pseudo-Release",
            release_node=pseudo_node,
        )
        cfg = SimpleNamespace(
            setting={
                "release_ars": True,
                "use_genres": True,
                "only_my_genres": False,
                "standardize_artist_names": StandardizeArtistNames.NONE,
                "translate_artist_names": False,
                "translate_artist_names_script_exception": False,
                "always_standardize_multivalue_artist": False,
                "standardize_instruments": True,
                "standardize_vocals": True,
                "translation_locales": ["en"],
            }
        )

        supplement_release_relationships_and_genres(album, orig_node, config_obj=cfg)

        rel_types = [r.get("type") for r in album._release_node["relations"]]
        self.assertIn("producer", rel_types)
        self.assertIn("amazon asin", rel_types)
        self.assertIn("mix-DJ", rel_types)
        # Forward transl-tracklisting relations from original release were not copied into pseudo-release
        self.assertEqual(rel_types.count("transl-tracklisting"), 1)

        # Real Picard _relations_to_metadata populated producer, asin, and per_medium_metadata
        self.assertEqual(album.metadata["producer"], "久石譲")
        self.assertEqual(album.metadata["asin"], "B00005L8N4")
        self.assertEqual(album.per_medium_metadata[1].getall("djmixer"), ["久石譲"])

        # Real Picard add_genres_from_node populated folksonomy tags and genres
        self.assertEqual(album._folksonomy_tags["studio ghibli"], 5)
        self.assertEqual(album._genres["anime"], 3)

    def test_genre_supplementation_failure_is_logged(self):
        album = MockAlbum("genre-failure")
        logger = MagicMock()
        config = SimpleNamespace(
            setting={"release_ars": False, "use_genres": True, "only_my_genres": False}
        )

        with patch.object(
            metadata_engine,
            "add_genres_from_node",
            side_effect=RuntimeError("genre conversion failed"),
        ):
            metadata_engine.supplement_release_relationships_and_genres(
                album,
                {"genres": [{"name": "rock", "count": 1}]},
                config_obj=config,
                logger_obj=logger,
            )

        logger.warning.assert_called_once_with(
            "Failed to process genres for pseudo-release: %s",
            unittest.mock.ANY,
        )


if __name__ == "__main__":
    unittest.main()
