# Real-world verification tests using captured MusicBrainz API JSON fixtures
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock

# Dynamically import plugin module
plugin_path = Path(__file__).resolve().parent.parent / '__init__.py'
spec = importlib.util.spec_from_file_location('pseudo_releases_plugin', str(plugin_path))
plugin_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin_module)

from caa_provider import PseudoReleaseCoverArtProvider
from candidates import (
    find_related_releases,
    select_best_original_candidate,
)
from constants import (
    TAG_ORIGINAL_RELEASE_ID,
)
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

    def __contains__(self, key):
        return key in self._data

    def get(self, key, default=""):
        val = self[key]
        return val if val else default

    def getall(self, key):
        return list(self._data.get(key, []))

    def copy(self, other):
        self._data = {k: list(v) for k, v in other._data.items()}


class MockAlbum:
    def __init__(self, album_id, title="", artist="", status="Pseudo-Release"):
        self.id = album_id
        self.metadata = MockMetadata(
            {
                "album": title,
                "albumartist": artist,
                "releasestatus": status.lower(),
                "musicbrainz_albumid": album_id,
            }
        )
        self.tracks = []
        self._finalized = False
        self.load_calls = []

    def _finalize_loading(self, error):
        self._finalized = True

    def load(self, **kwargs):
        self.load_calls.append(kwargs)

    def iterfiles(self):
        return iter([])



class MockPluginConfig(dict):
    def register_option(self, name, default):
        if name not in self:
            self[name] = default


class MockPluginApi:
    def __init__(self, initial_config=None):
        defaults = {}
        if initial_config:
            defaults.update(initial_config)
        self.plugin_config = MockPluginConfig(defaults)
        self.tagger = SimpleNamespace(
            window=SimpleNamespace(selected_objects=[]),
            config=self.plugin_config,
        )
        self.processors = []
        self.providers = []
        self.album_actions = []
        self.options_pages = []
        self.removal_processors = []
        self.added_tasks = []
        self.completed_tasks = []
        self.logger = MagicMock()
        self.mb_api = MagicMock()

    def tr(self, key, text=None):
        return text or key

    def trn(self, singular, plural, n=1):
        return singular if n == 1 else plural


    def register_album_metadata_processor(self, func, priority=50):
        self.processors.append((func, priority))

    def register_album_post_removal_processor(self, func):
        self.removal_processors.append(func)

    def register_album_action(self, action_cls):
        action_cls.api = self
        self.album_actions.append(action_cls)

    def register_cover_art_provider(self, provider_cls):
        self.providers.append(provider_cls)

    def register_options_page(self, page_cls):
        self.options_pages.append(page_cls)

    def register_script_variable(self, name, documentation="", title="", **kwargs):
        pass


    def add_album_task(self, album, task_id, description, timeout, request_factory, blocking=False):
        self.added_tasks.append((album, task_id, blocking))
        self.metadata_at_task_add = album.metadata.get(TAG_ORIGINAL_RELEASE_ID)
        if request_factory:
            request_factory()

    def complete_album_task(self, album, task_id):
        self.completed_tasks.append((album, task_id))


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
        self.assertTrue(any(task[1] == "pseudo_enrich_7a16f215-079e-4c55-abda-06f9a4228b6a" for task in self.api.completed_tasks))
        self.assertTrue(pseudo_album._finalized)

        # 2. Assert enriched catalog metadata
        meta = pseudo_album.metadata
        self.assertEqual(meta["date"], "2001-07-18")
        self.assertEqual(meta["releasecountry"], "JP")
        self.assertEqual(meta["barcode"], "4988008604535")
        self.assertEqual(meta["media"], "CD")
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

    def test_real_release_non_pseudo_ignored(self):
        """Test: Official non-pseudo release is never enriched."""
        official_album = MockAlbum(
            album_id="7a16f215-079e-4c55-abda-06f9a4228b6a",
            title="Standard release",
            status="Official",
        )

        plugin_module.PseudoReleasePlugin.process_album_metadata(
            api=self.api,
            album=official_album,
            album_metadata=official_album.metadata,
            release_node={"id": "7a16f215-079e-4c55-abda-06f9a4228b6a", "status": "Official"},
        )

        self.assertEqual(self.api.added_tasks, [])
        self.assertEqual(official_album.metadata[TAG_ORIGINAL_RELEASE_ID], "")

    def test_real_release_automatic_supplementation(self):
        """Test: Automatic supplementation enriches catalog tags from linked original release."""
        pseudo_node = load_fixture("9fe92739-5bcd-4f6e-b2f2-d2db97cabc32")
        orig_node = load_fixture("7a16f215-079e-4c55-abda-06f9a4228b6a")

        api = MockPluginApi()
        pseudo_album = MockAlbum(
            album_id=pseudo_node["id"],
            title=pseudo_node["title"],
            status="Pseudo-Release",
        )

        def mock_get(rel_id, cb, inc=None, **kwargs):
            cb(orig_node, None, None)

        api.mb_api.get_release_by_id.side_effect = mock_get

        plugin_module.PseudoReleasePlugin.process_album_metadata(
            api=api,
            album=pseudo_album,
            album_metadata=pseudo_album.metadata,
            release_node=pseudo_node,
        )

        meta = pseudo_album.metadata
        self.assertEqual(meta["date"], "2001-07-18")
        self.assertEqual(meta["releasecountry"], "JP")
        self.assertEqual(meta["barcode"], "4988008604535")
        self.assertEqual(meta[TAG_ORIGINAL_RELEASE_ID], "7a16f215-079e-4c55-abda-06f9a4228b6a")

    def test_real_release_set_original_id_tag(self):
        """Test: The ~original_musicbrainz_albumid tag is populated with the linked original release ID."""
        pseudo_node = load_fixture("ea59c77e-1c73-4958-88fb-d86e89fb3018")
        orig_node = load_fixture("1268ebdb-2fa4-423f-95da-ed7accfbb845")

        pseudo_album = MockAlbum(
            album_id=pseudo_node["id"],
            title=pseudo_node["title"],
            status="Pseudo-Release",
        )

        def mock_get(rel_id, cb, inc=None, **kwargs):
            cb(orig_node, None, None)

        self.api.mb_api.get_release_by_id.side_effect = mock_get

        plugin_module.PseudoReleasePlugin.process_album_metadata(
            api=self.api,
            album=pseudo_album,
            album_metadata=pseudo_album.metadata,
            release_node=pseudo_node,
        )

        meta = pseudo_album.metadata
        self.assertEqual(meta["barcode"], "4942463526528")
        self.assertEqual(meta[TAG_ORIGINAL_RELEASE_ID], "1268ebdb-2fa4-423f-95da-ed7accfbb845")

    def test_real_release_cover_art_enabled(self):
        """CAA provider test: When original release ID is present, CAA provider routes to original MBID."""
        pseudo_node = load_fixture("9fe92739-5bcd-4f6e-b2f2-d2db97cabc32")
        orig_node = load_fixture("7a16f215-079e-4c55-abda-06f9a4228b6a")

        pseudo_album = MockAlbum(
            album_id=pseudo_node["id"],
            title=pseudo_node["title"],
            status="Pseudo-Release",
        )

        def mock_get(rel_id, cb, inc=None, **kwargs):
            cb(orig_node, None, None)

        self.api.mb_api.get_release_by_id.side_effect = mock_get

        plugin_module.PseudoReleasePlugin.process_album_metadata(
            api=self.api,
            album=pseudo_album,
            album_metadata=pseudo_album.metadata,
            release_node=pseudo_node,
        )

        # Metadata was supplemented
        self.assertEqual(pseudo_album.metadata["barcode"], "4988008604535")
        self.assertEqual(pseudo_album.metadata[TAG_ORIGINAL_RELEASE_ID], "7a16f215-079e-4c55-abda-06f9a4228b6a")

        # CAA provider is enabled and resolves original MBID path
        mock_coverart = SimpleNamespace(
            album=pseudo_album,
            metadata=pseudo_album.metadata,
            release=pseudo_node,
            tagger=self.api.tagger,
            front_image_found=False,
        )
        caa_provider = PseudoReleaseCoverArtProvider(mock_coverart)
        self.assertTrue(caa_provider.enabled())
        self.assertEqual(caa_provider._caa_path, "/release/7a16f215-079e-4c55-abda-06f9a4228b6a/")

    def test_real_release_context_menu_options(self):
        """Test: Linked original editions action shows and formats candidates correctly."""
        pseudo_node = load_fixture("9fe92739-5bcd-4f6e-b2f2-d2db97cabc32")
        orig_node = load_fixture("7a16f215-079e-4c55-abda-06f9a4228b6a")

        pseudo_album = MockAlbum(
            album_id=pseudo_node["id"],
            title=pseudo_node["title"],
            status="Pseudo-Release",
        )
        pseudo_album._pseudo_original_candidates = [orig_node]
        self.api.tagger.window.selected_objects = [pseudo_album]

        # Action is enabled when auto_supplement is on
        action_enabled = plugin_module.ChooseLinkedOriginalAction()
        self.assertTrue(action_enabled.isEnabled())

        # Candidate label formatting verification
        formatted_label = plugin_module.PseudoReleasePlugin._format_original_candidate(orig_node)
        self.assertIn("2001", formatted_label)
        self.assertIn("JP", formatted_label)
        self.assertIn("CD", formatted_label)
        self.assertIn("TKCA-72165", formatted_label)

        # Tooltip formatting verification
        tooltip = plugin_module.PseudoReleasePlugin._format_original_candidate_tooltip(orig_node)
        self.assertIn("4988008604535", tooltip)
        self.assertIn("Middle-click or right-click to open in browser.", tooltip)

        # Catalog number deduplication test with Minimoni candidate (1268ebdb)
        minimoni_orig = load_fixture("1268ebdb-2fa4-423f-95da-ed7accfbb845")
        minimoni_label = plugin_module.PseudoReleasePlugin._format_original_candidate(minimoni_orig)
        self.assertEqual(minimoni_label.count("EPCE-5265"), 1)
        self.assertTrue(minimoni_label.endswith("zetima / EPCE-5265"))

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

        # Multi-disc format and tooltip extra fields verification
        multi_cand = {
            "id": "multi-cand-1",
            "date": "2020-05-10",
            "country": "US",
            "media": [
                {"format": "CD", "track-count": 10},
                {"format": "CD", "track-count": 12},
            ],
            "label-info": [
                {"label": {"name": "MultiLabel"}, "catalog-number": "ML-001"},
            ],
            "packaging": "Jewel Case",
            "disambiguation": "Special Edition",
        }
        multi_label = plugin_module.PseudoReleasePlugin._format_original_candidate(multi_cand)
        self.assertIn("2×CD", multi_label)
        self.assertIn("10+12", multi_label)
        self.assertIn("2020", multi_label)
        self.assertIn("US", multi_label)
        self.assertIn("MultiLabel", multi_label)
        self.assertIn("ML-001", multi_label)

        multi_tooltip = plugin_module.PseudoReleasePlugin._format_original_candidate_tooltip(multi_cand)
        self.assertIn("Jewel Case", multi_tooltip)
        self.assertIn("Special Edition", multi_tooltip)
        self.assertIn("[no barcode]", multi_tooltip)

        # Null-safety test: release-events = None (crashes Picard _release_event_iter if unhandled)
        null_events_cand = {
            "id": "null-events-cand",
            "date": "2021-01-01",
            "country": "JP",
            "release-events": None,
            "media": [{"format": "CD", "track-count": 5}],
        }
        null_label = plugin_module.PseudoReleasePlugin._format_original_candidate(null_events_cand)
        self.assertIn("JP", null_label)
        self.assertIn("5", null_label)

        # >10 media truncation test: Picard's VERSIONS_MAX_TRACKS truncation with +…
        boxset_cand = {
            "id": "boxset-cand",
            "date": "2022-03-15",
            "country": "GB",
            "media": [{"format": "CD", "track-count": 10}] * 12,
        }
        boxset_label = plugin_module.PseudoReleasePlugin._format_original_candidate(boxset_cand)
        self.assertIn("+".join(["10"] * 10) + "+…", boxset_label)
        self.assertNotIn("+".join(["10"] * 12), boxset_label)

        # Null-safety test: media tracks = None and malformed label-info = [None]
        malformed_cand = {
            "id": "malformed-cand",
            "media": [{"format": "CD", "track-count": None, "tracks": None}],
            "label-info": [None],
        }
        malformed_label = plugin_module.PseudoReleasePlugin._format_original_candidate(malformed_cand)
        self.assertIn("??", malformed_label)

        # Robustness test: candidate = None and non-list field types
        none_label = plugin_module.PseudoReleasePlugin._format_original_candidate(None)
        self.assertIn("??", none_label)
        none_tooltip = plugin_module.PseudoReleasePlugin._format_original_candidate_tooltip(None)
        self.assertIn("[no barcode]", none_tooltip)

        for invalid_field_cand in [
            {"media": 123},
            {"label-info": 123},
            {"release-events": 123},
            {"release-events": "JP"},
        ]:
            inv_label = plugin_module.PseudoReleasePlugin._format_original_candidate(invalid_field_cand)
            self.assertIn("??", inv_label)

        # Exotic packaging attribute test
        exotic_cand = {
            "id": "exotic-cand",
            "packaging": "Exotic 3D Holo-Box",
        }
        exotic_tooltip = plugin_module.PseudoReleasePlugin._format_original_candidate_tooltip(exotic_cand)
        self.assertIn("Exotic 3D Holo-Box", exotic_tooltip)

        # Advanced type robustness: int date, int country, int format, int tracks, int label/catnum
        int_fields_cand = {
            "date": 2020,
            "country": 123,
            "media": [
                {"format": 123, "track-count": 5},
                {"track-count": None, "tracks": 123},
            ],
            "label-info": [
                {"label": {"name": 123}, "catalog-number": 456},
            ],
        }
        int_label = plugin_module.PseudoReleasePlugin._format_original_candidate(int_fields_cand)
        self.assertIn("2020", int_label)
        self.assertIn("123", int_label)
        self.assertIn("456", int_label)

        # Tooltip int field values robustness
        int_tooltip = plugin_module.PseudoReleasePlugin._format_original_candidate_tooltip({
            "packaging": 123,
            "barcode": 456,
            "disambiguation": 789,
        })
        self.assertIn("123", int_tooltip)
        self.assertIn("456", int_tooltip)
        self.assertIn("789", int_tooltip)

        # Plugin lifecycle null and malformed dispatch safety
        plugin_module.PseudoReleasePlugin.process_album_metadata(
            self.api,
            MockAlbum(album_id="album-null"),
            MockMetadata(),
            None,
        )
        plugin_module.PseudoReleasePlugin._prefetch_linked_original_details(
            self.api,
            MockAlbum(album_id="album-prefetch"),
            [None],
            None,
        )
        plugin_module.PseudoReleasePlugin._handle_supplement_pseudo(
            self.api,
            MockAlbum(album_id="album-none"),
            MockMetadata(),
            "target-none",
            [None],
        )

        # In-flight state leak prevention when api cannot schedule task
        test_album = MockAlbum(album_id="album-leak-test")
        plugin_module.PseudoReleasePlugin.in_flight_albums.clear()
        failing_api = MockPluginApi()
        failing_api.add_album_task = unittest.mock.MagicMock(
            side_effect=RuntimeError("Scheduler error")
        )
        with self.assertRaises(RuntimeError):
            plugin_module.PseudoReleasePlugin._queue_enrichment(
                failing_api,
                test_album,
                "target-mbid-1",
            )
        self.assertNotIn("album-leak-test", plugin_module.PseudoReleasePlugin.in_flight_albums)


if __name__ == '__main__':
    unittest.main()
