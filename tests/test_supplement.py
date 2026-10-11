# Tests for pseudo-release metadata supplementation
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

    def __contains__(self, key):
        return key in self._data

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
        self.assertNotIn("originaldate", catalog)
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
        self.assertEqual(pseudo_meta["originaldate"], "")
        self.assertEqual(pseudo_meta["releasecountry"], "JP")
        self.assertEqual(pseudo_meta["barcode"], "4988008610134")
        self.assertEqual(pseudo_meta["media"], "CD")
        self.assertEqual(pseudo_meta.getall("label"), ["Tokuma Japan Communications"])
        self.assertEqual(pseudo_meta.getall("catalognumber"), ["TKCA-72165"])
        self.assertEqual(pseudo_meta[TAG_ORIGINAL_RELEASE_ID], "7a16f215-079e-4c55-abda-06f9a4228b6a")

        # Titles must remain unchanged
        self.assertEqual(pseudo_meta["album"], "Spirited Away: Original Soundtrack")
        self.assertEqual(pseudo_meta["albumartist"], "Joe Hisaishi")

    def test_supplement_overwrites_by_default(self):
        # Default behavior: preserve_existing is False, so existing tags get overwritten
        pseudo_meta = MockMetadata(
            {
                "album": "Spirited Away",
                "date": "1999-01-01",
                "releasecountry": "US",
            }
        )
        orig_node = {
            "id": "orig-123",
            "date": "2001-07-18",
            "country": "JP",
            "barcode": "4988008610134",
        }

        supplement_pseudo_metadata(pseudo_meta, orig_node, preserve_existing=False)

        self.assertEqual(pseudo_meta["date"], "2001-07-18")
        self.assertEqual(pseudo_meta["releasecountry"], "JP")
        self.assertEqual(pseudo_meta["barcode"], "4988008610134")

    def test_supplement_preserves_existing_when_enabled(self):
        # When preserve_existing is True, existing tags must NOT be overwritten
        pseudo_meta = MockMetadata(
            {
                "album": "Spirited Away",
                "date": "1999-01-01",
                "releasecountry": "US",
            }
        )
        orig_node = {
            "id": "orig-123",
            "date": "2001-07-18",
            "country": "JP",
            "barcode": "4988008610134",
        }

        supplement_pseudo_metadata(pseudo_meta, orig_node, preserve_existing=True)

        self.assertEqual(pseudo_meta["date"], "1999-01-01")
        self.assertEqual(pseudo_meta["releasecountry"], "US")
        self.assertEqual(pseudo_meta["barcode"], "4988008610134")

    def test_supplement_omits_original_id_tag_when_disabled(self):
        pseudo_meta = MockMetadata({"album": "Spirited Away"})
        orig_node = {"id": "orig-123", "date": "2001-07-18"}

        supplement_pseudo_metadata(pseudo_meta, orig_node, set_original_id=False)

        self.assertEqual(pseudo_meta["date"], "2001-07-18")
        self.assertNotIn(TAG_ORIGINAL_RELEASE_ID, pseudo_meta._data)

    def test_get_enrichment_inc_params(self):
        from types import SimpleNamespace
        from metadata_engine import get_enrichment_inc_params

        # Default: no ARs, no genres
        cfg_default = SimpleNamespace(setting={"release_ars": False, "use_genres": False})
        params = get_enrichment_inc_params(cfg_default)
        self.assertIn("labels", params)
        self.assertIn("media", params)
        self.assertNotIn("artist-rels", params)
        self.assertNotIn("tags", params)

        # release_ars = True
        cfg_ars = SimpleNamespace(setting={"release_ars": True, "use_genres": False})
        params_ars = get_enrichment_inc_params(cfg_ars)
        self.assertIn("artist-rels", params_ars)
        self.assertIn("url-rels", params_ars)
        self.assertIn("series-rels", params_ars)
        self.assertIn("label-rels", params_ars)
        self.assertNotIn("tags", params_ars)

        # use_genres = True
        cfg_genres = SimpleNamespace(setting={"release_ars": False, "use_genres": True, "only_my_genres": False})
        params_genres = get_enrichment_inc_params(cfg_genres)
        self.assertIn("tags", params_genres)
        self.assertIn("genres", params_genres)
        self.assertNotIn("artist-rels", params_genres)

        # only_my_genres = True
        cfg_user_genres = SimpleNamespace(setting={"release_ars": False, "use_genres": True, "only_my_genres": True})
        params_user_genres = get_enrichment_inc_params(cfg_user_genres)
        self.assertIn("user-tags", params_user_genres)
        self.assertIn("user-genres", params_user_genres)

    def test_supplement_relationships_and_genres(self):
        from types import SimpleNamespace
        from collections import Counter
        from metadata_engine import supplement_release_relationships_and_genres

        class DummyAlbum:
            def __init__(self):
                self._release_node = {
                    "id": "pseudo-1",
                    "relations": [
                        {
                            "type": "transl-tracklisting",
                            "direction": "backward",
                            "target-type": "release",
                            "release": {"id": "orig-1"},
                        }
                    ],
                }
                self.metadata = MockMetadata()
                self._folksonomy_tags = Counter()
                self._genres = Counter()
                self.tracks = []

            def add_folksonomy_tag(self, name, count):
                self._folksonomy_tags[name] += count

            def add_genre(self, name, count):
                self._genres[name] += count

        orig_node = {
            "id": "orig-1",
            "relations": [
                {
                    "type": "design/illustration",
                    "target-type": "artist",
                    "artist": {"id": "artist-tadano", "name": "只野和子"},
                },
                {
                    "type": "transl-tracklisting",
                    "direction": "forward",
                    "target-type": "release",
                    "release": {"id": "pseudo-1"},
                },
                {
                    "type": "amazon asin",
                    "target-type": "url",
                    "url": {"resource": "https://www.amazon.co.jp/dp/B00005GLB2"},
                },
            ],
            "tags": [{"name": "美少女戦士セーラームーン", "count": 5}],
            "genres": [{"name": "anime", "count": 3}],
        }

        album = DummyAlbum()
        cfg = SimpleNamespace(setting={"release_ars": True, "use_genres": True, "only_my_genres": False})

        supplement_release_relationships_and_genres(album, orig_node, config_obj=cfg)

        # Relations were merged into _release_node (skipping self-referential transl-tracklisting)
        rel_types = [r.get("type") for r in album._release_node["relations"]]
        self.assertIn("design/illustration", rel_types)
        self.assertIn("amazon asin", rel_types)
        # transl-tracklisting not duplicated
        self.assertEqual(rel_types.count("transl-tracklisting"), 1)

        # Tags and genres stored on release_node
        self.assertEqual(album._release_node["tags"], [{"name": "美少女戦士セーラームーン", "count": 5}])
        self.assertEqual(album._release_node["genres"], [{"name": "anime", "count": 3}])
        # album item received folksonomy tags and genres
        self.assertEqual(album._folksonomy_tags["美少女戦士セーラームーン"], 5)
        # Null and invalid type safety verification
        self.assertEqual(extract_release_catalog_metadata(None), {})
        self.assertEqual(extract_release_catalog_metadata({"media": 123, "label-info": 123}), {})

        dummy_meta = MockMetadata()
        supplement_pseudo_metadata(dummy_meta, None)
        self.assertEqual(dummy_meta._data, {})

        supplement_release_relationships_and_genres(None, None)
        supplement_release_relationships_and_genres(
            album,
            {"relations": 123, "tags": 123, "genres": 123},
            config_obj=cfg,
        )


if __name__ == '__main__':
    unittest.main()
