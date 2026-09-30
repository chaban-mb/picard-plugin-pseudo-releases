# Integration tests for plugin lifecycle, task queues, and processor integration
import unittest
from unittest.mock import MagicMock
import importlib.util
from pathlib import Path

plugin_path = Path(__file__).resolve().parent.parent / '__init__.py'
spec = importlib.util.spec_from_file_location('pseudo_releases_plugin', str(plugin_path))
plugin_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin_module)

from constants import (
    OPT_AUTO_OVERLAY,
    OPT_AUTO_SUPPLEMENT,
    OPT_ENABLED,
    OPT_SKIP_LATIN_ORIGINALS,
    OPT_TARGET_SCRIPT_MODE,
    SCRIPT_MODE_LATN,
    TAG_ORIGINAL_RELEASE_ID,
    TAG_PSEUDO_RELEASE_ID,
)


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
    def __init__(self, album_id, title="", artist="", status="Official"):
        self.id = album_id
        self.metadata = MockMetadata(
            {
                "album": title,
                "albumartist": artist,
                "releasestatus": status.lower(),
            }
        )
        self.tracks = []
        self._finalized = False

    def _finalize_loading(self, error):
        self._finalized = True


class MockPluginConfig(dict):
    def register_option(self, name, default):
        if name not in self:
            self[name] = default


class MockPluginApi:
    def __init__(self):
        self.plugin_config = MockPluginConfig({
            OPT_ENABLED: True,
            OPT_AUTO_SUPPLEMENT: True,
            OPT_AUTO_OVERLAY: True,
            OPT_TARGET_SCRIPT_MODE: SCRIPT_MODE_LATN,
            OPT_SKIP_LATIN_ORIGINALS: True,
        })
        self.processors = []

        self.providers = []
        self.options_pages = []
        self.removal_processors = []
        self.added_tasks = []
        self.completed_tasks = []
        self.logger = MagicMock()
        self.mb_api = MagicMock()

    def register_album_metadata_processor(self, func, priority=50):
        self.processors.append((func, priority))

    def register_track_metadata_processor(self, func, priority=50):
        self.processors.append((func, priority))

    def register_album_post_removal_processor(self, func):
        self.removal_processors.append(func)

    def register_cover_art_provider(self, provider_cls):
        self.providers.append(provider_cls)

    def register_options_page(self, page_cls):
        self.options_pages.append(page_cls)

    def add_album_task(self, album, task_id, description, timeout, request_factory, blocking=False):
        self.added_tasks.append((album, task_id, blocking))
        if request_factory:
            request_factory()

    def complete_album_task(self, album, task_id):
        self.completed_tasks.append((album, task_id))


class TestPluginLifecycle(unittest.TestCase):
    def setUp(self):
        self.api = MockPluginApi()
        plugin_module.enable(self.api)

    def test_enable_registers_extension_points(self):
        self.assertTrue(len(self.api.processors) > 0)
        self.assertTrue(len(self.api.removal_processors) > 0)
        self.assertTrue(len(self.api.providers) > 0)
        self.assertTrue(len(self.api.options_pages) > 0)

    def test_direction_1_supplement_pseudo_release(self):
        # A loaded pseudo-release with backward link to original
        pseudo_album = MockAlbum("pseudo-1", title="Spirited Away", artist="Joe Hisaishi", status="Pseudo-Release")

        pseudo_node = {
            "id": "pseudo-1",
            "status": "Pseudo-Release",
            "relations": [
                {
                    "type": "transl-tracklisting",
                    "direction": "backward",
                    "release": {
                        "id": "orig-1",
                        "title": "千と千尋の神隠し",
                        "status": "Official",
                        "barcode": "4988008610134",
                        "date": "2001-07-18",
                        "country": "JP",
                    },
                }
            ],
        }

        # Mock the mb_api.get_release_by_id to simulate network return
        def mock_get_release(rel_id, callback, inc=None):
            orig_doc = {
                "id": "orig-1",
                "title": "千と千尋の神隠し",
                "barcode": "4988008610134",
                "date": "2001-07-18",
                "country": "JP",
                "media": [{"format": "CD"}],
                "label-info": [{"label": {"name": "Tokuma"}}],
            }
            callback(orig_doc, None, None)

        self.api.mb_api.get_release_by_id.side_effect = mock_get_release

        # Trigger metadata processor
        plugin_module.PseudoReleasePlugin.process_album_metadata(
            api=self.api,
            album=pseudo_album,
            album_metadata=pseudo_album.metadata,
            release_node=pseudo_node,
        )

        # Assert album task was added with blocking=True and completed
        self.assertTrue(any(task[1] == "pseudo_enrich_orig-1" and task[2] is True for task in self.api.added_tasks))
        self.assertTrue(any(task[1] == "pseudo_enrich_orig-1" for task in self.api.completed_tasks))

        # Assert metadata supplementation succeeded
        self.assertEqual(pseudo_album.metadata["barcode"], "4988008610134")
        self.assertEqual(pseudo_album.metadata["date"], "2001-07-18")
        self.assertEqual(pseudo_album.metadata["releasecountry"], "JP")
        self.assertEqual(pseudo_album.metadata["label"], "Tokuma")
        self.assertEqual(pseudo_album.metadata[TAG_ORIGINAL_RELEASE_ID], "orig-1")

        # Assert finalization kick was triggered
        self.assertTrue(pseudo_album._finalized)

    def test_direction_2_overlay_original_release(self):
        # A loaded Japanese Kanji release with forward link to Romaji pseudo-release
        orig_album = MockAlbum("orig-1", title="千と千尋の神隠し", artist="久石譲", status="Official")

        orig_node = {
            "id": "orig-1",
            "status": "Official",
            "text-representation": {"script": "Jpan", "language": "jpn"},
            "relations": [
                {
                    "type": "transl-tracklisting",
                    "direction": "forward",
                    "release": {
                        "id": "pseudo-romaji",
                        "title": "Sen to Chihiro no Kamikakushi",
                        "status": "Pseudo-Release",
                        "text-representation": {"script": "Latn", "language": "jpn"},
                    },
                }
            ],
        }

        def mock_get_release(rel_id, callback, inc=None):
            pseudo_doc = {
                "id": "pseudo-romaji",
                "title": "Sen to Chihiro no Kamikakushi",
                "artist-credit": [
                    {
                        "name": "Joe Hisaishi",
                        "joinphrase": "",
                        "artist": {"name": "Joe Hisaishi", "sort-name": "Hisaishi, Joe"},
                    }
                ],
                "media": [],
            }
            callback(pseudo_doc, None, None)

        self.api.mb_api.get_release_by_id.side_effect = mock_get_release

        # Trigger metadata processor
        plugin_module.PseudoReleasePlugin.process_album_metadata(
            api=self.api,
            album=orig_album,
            album_metadata=orig_album.metadata,
            release_node=orig_node,
        )

        # Assert overlay succeeded
        self.assertEqual(orig_album.metadata["album"], "Sen to Chihiro no Kamikakushi")
        self.assertEqual(orig_album.metadata["albumartist"], "Joe Hisaishi")
        self.assertEqual(orig_album.metadata[TAG_PSEUDO_RELEASE_ID], "pseudo-romaji")
        self.assertEqual(orig_album.metadata["~original_album"], "千と千尋の神隠し")

        # Assert finalization kick was triggered
        self.assertTrue(orig_album._finalized)

    def test_remove_album_cleans_up_in_flight(self):
        plugin_module.PseudoReleasePlugin.in_flight_albums.add("album-to-remove")
        dummy_album = MockAlbum("album-to-remove")

        plugin_module.PseudoReleasePlugin.remove_album(self.api, dummy_album)
        self.assertNotIn("album-to-remove", plugin_module.PseudoReleasePlugin.in_flight_albums)

    def test_process_track_metadata(self):
        orig_album = MockAlbum("orig-123", "Orig Album")
        orig_album._pseudo_tracks = {
            "rec-1": {"title": "Translated Track 1", "artist-credit": [{"name": "English Artist"}]},
            "1:2": {"title": "Translated Track 2", "artist-credit": [{"name": "English Artist 2"}]},
        }

        class MockTrackItem:
            album = orig_album

        # Test match by recording id
        track1 = MockTrackItem()
        meta1 = MockMetadata({"musicbrainz_recordingid": "rec-1", "title": "Japanese Track 1"})
        plugin_module.PseudoReleasePlugin.process_track_metadata(
            self.api, track1, meta1, {"recording": {"id": "rec-1"}}, None
        )
        self.assertEqual(meta1["title"], "Translated Track 1")
        self.assertEqual(meta1["artist"], "English Artist")

        # Test match by position fallback
        track2 = MockTrackItem()
        meta2 = MockMetadata({"discnumber": "1", "tracknumber": "2", "title": "Japanese Track 2"})
        plugin_module.PseudoReleasePlugin.process_track_metadata(
            self.api, track2, meta2, {}, None
        )
        self.assertEqual(meta2["title"], "Translated Track 2")
        self.assertEqual(meta2["artist"], "English Artist 2")


if __name__ == '__main__':
    unittest.main()
