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
    OPT_AUTO_SUPPLEMENT,
    OPT_ENABLE_ORIGINAL_COVER_ART,
    OPT_PRESERVE_EXISTING_TAGS,
    OPT_SET_ORIGINAL_RELEASE_ID,
    OPT_SHOW_CONTEXT_MENU,
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


class MockPluginConfig(dict):
    def register_option(self, name, default):
        if name not in self:
            self[name] = default


class MockPluginApi:
    def __init__(self, initial_config=None):
        defaults = {
            OPT_AUTO_SUPPLEMENT: True,
            OPT_PRESERVE_EXISTING_TAGS: False,
            OPT_SET_ORIGINAL_RELEASE_ID: True,
            OPT_ENABLE_ORIGINAL_COVER_ART: True,
            OPT_SHOW_CONTEXT_MENU: True,
        }
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

        def mock_get_release(rel_id, callback, inc=None):
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
        self.assertEqual(meta["originaldate"], "2001-07-18")
        self.assertEqual(meta["releasecountry"], "JP")
        self.assertEqual(meta["barcode"], "4988008604535")
        self.assertEqual(meta["media"], "CD")
        self.assertEqual(meta.getall("catalognumber"), ["TKCA-72165"])
        self.assertEqual(meta.getall("label"), ["STUDIO GHIBLI RECORDS"])
        self.assertEqual(meta[TAG_ORIGINAL_RELEASE_ID], "7a16f215-079e-4c55-abda-06f9a4228b6a")

        # 3. Assert Romaji title was preserved
        self.assertEqual(meta["album"], "Sen to Chihiro no Kamikakushi")

        # 4. Assert CAA provider routes to original release
        caa_provider = PseudoReleaseCoverArtProvider()
        caa_provider.metadata = meta
        caa_provider.album = pseudo_album
        caa_provider.coverart = SimpleNamespace(album=pseudo_album, tagger=self.api.tagger, front_image_found=False)
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

        def mock_get_release(rel_id, callback, inc=None):
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

        def mock_get_release(rel_id, callback, inc=None):
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

    def test_real_release_auto_supplement_disabled(self):
        """Option Test: When OPT_AUTO_SUPPLEMENT is False, no enrichment occurs."""
        self.api.plugin_config[OPT_AUTO_SUPPLEMENT] = False

        pseudo_node = load_fixture("9fe92739-5bcd-4f6e-b2f2-d2db97cabc32")
        pseudo_album = MockAlbum(
            album_id=pseudo_node["id"],
            title=pseudo_node["title"],
            status="Pseudo-Release",
        )

        plugin_module.PseudoReleasePlugin.process_album_metadata(
            api=self.api,
            album=pseudo_album,
            album_metadata=pseudo_album.metadata,
            release_node=pseudo_node,
        )

        # No background requests or enrichment should occur
        self.assertEqual(self.api.added_tasks, [])
        self.assertEqual(pseudo_album.metadata["date"], "")
        self.assertEqual(pseudo_album.metadata[TAG_ORIGINAL_RELEASE_ID], "")

    def test_real_release_preserve_existing_tags_option(self):
        """Option Test: OPT_PRESERVE_EXISTING_TAGS=False overwrites existing tags,
        while OPT_PRESERVE_EXISTING_TAGS=True preserves them.
        """
        pseudo_node = load_fixture("9fe92739-5bcd-4f6e-b2f2-d2db97cabc32")
        orig_node = load_fixture("7a16f215-079e-4c55-abda-06f9a4228b6a")

        def run_supplementation(preserve: bool) -> MockMetadata:
            api = MockPluginApi({OPT_PRESERVE_EXISTING_TAGS: preserve})
            pseudo_album = MockAlbum(
                album_id=pseudo_node["id"],
                title=pseudo_node["title"],
                status="Pseudo-Release",
            )
            # Pre-populate custom date and country
            pseudo_album.metadata["date"] = "1999-01-01"
            pseudo_album.metadata["releasecountry"] = "US"

            def mock_get(rel_id, cb, inc=None):
                cb(orig_node, None, None)

            api.mb_api.get_release_by_id.side_effect = mock_get

            plugin_module.PseudoReleasePlugin.process_album_metadata(
                api=api,
                album=pseudo_album,
                album_metadata=pseudo_album.metadata,
                release_node=pseudo_node,
            )
            return pseudo_album.metadata

        # Case A: False (default) -> Overwrites date and country with original values
        meta_overwritten = run_supplementation(preserve=False)
        self.assertEqual(meta_overwritten["date"], "2001-07-18")
        self.assertEqual(meta_overwritten["releasecountry"], "JP")
        self.assertEqual(meta_overwritten["barcode"], "4988008604535")

        # Case B: True -> Preserves existing date and country
        meta_preserved = run_supplementation(preserve=True)
        self.assertEqual(meta_preserved["date"], "1999-01-01")
        self.assertEqual(meta_preserved["releasecountry"], "US")
        self.assertEqual(meta_preserved["barcode"], "4988008604535")

    def test_real_release_set_original_id_tag_option(self):
        """Option Test: When OPT_SET_ORIGINAL_RELEASE_ID is False, the tag is omitted."""
        self.api.plugin_config[OPT_SET_ORIGINAL_RELEASE_ID] = False

        pseudo_node = load_fixture("ea59c77e-1c73-4958-88fb-d86e89fb3018")
        orig_node = load_fixture("1268ebdb-2fa4-423f-95da-ed7accfbb845")

        pseudo_album = MockAlbum(
            album_id=pseudo_node["id"],
            title=pseudo_node["title"],
            status="Pseudo-Release",
        )

        def mock_get(rel_id, cb, inc=None):
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
        self.assertNotIn(TAG_ORIGINAL_RELEASE_ID, meta._data)

    def test_real_release_cover_art_disabled_option(self):
        """Option Test: When OPT_ENABLE_ORIGINAL_COVER_ART is False, CAA provider is disabled."""
        self.api.plugin_config[OPT_ENABLE_ORIGINAL_COVER_ART] = False

        pseudo_node = load_fixture("9fe92739-5bcd-4f6e-b2f2-d2db97cabc32")
        orig_node = load_fixture("7a16f215-079e-4c55-abda-06f9a4228b6a")

        pseudo_album = MockAlbum(
            album_id=pseudo_node["id"],
            title=pseudo_node["title"],
            status="Pseudo-Release",
        )

        def mock_get(rel_id, cb, inc=None):
            cb(orig_node, None, None)

        self.api.mb_api.get_release_by_id.side_effect = mock_get

        plugin_module.PseudoReleasePlugin.process_album_metadata(
            api=self.api,
            album=pseudo_album,
            album_metadata=pseudo_album.metadata,
            release_node=pseudo_node,
        )

        # Metadata was still supplemented
        self.assertEqual(pseudo_album.metadata["barcode"], "4988008604535")

        # But CAA provider is disabled via config
        caa_provider = PseudoReleaseCoverArtProvider()
        caa_provider.metadata = pseudo_album.metadata
        caa_provider.coverart = SimpleNamespace(album=pseudo_album, tagger=self.api.tagger, front_image_found=False)
        self.assertFalse(caa_provider.enabled())

    def test_real_release_context_menu_options(self):
        """Option Test: Context menu reflects OPT_SHOW_CONTEXT_MENU option with real candidates."""
        pseudo_node = load_fixture("9fe92739-5bcd-4f6e-b2f2-d2db97cabc32")
        orig_node = load_fixture("7a16f215-079e-4c55-abda-06f9a4228b6a")

        pseudo_album = MockAlbum(
            album_id=pseudo_node["id"],
            title=pseudo_node["title"],
            status="Pseudo-Release",
        )
        pseudo_album._pseudo_original_candidates = [orig_node]
        self.api.tagger.window.selected_objects = [pseudo_album]

        # Case A: Enabled (default)
        self.api.plugin_config[OPT_SHOW_CONTEXT_MENU] = True
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

        # Case B: Disabled
        self.api.plugin_config[OPT_SHOW_CONTEXT_MENU] = False
        action_disabled = plugin_module.ChooseLinkedOriginalAction()
        self.assertFalse(action_disabled.isEnabled())


if __name__ == '__main__':
    unittest.main()
