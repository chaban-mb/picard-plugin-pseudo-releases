# Integration tests for plugin lifecycle, task queues, and processor integration
import unittest
from unittest.mock import MagicMock
import importlib.util
from pathlib import Path
from types import SimpleNamespace

plugin_path = Path(__file__).resolve().parent.parent / '__init__.py'
spec = importlib.util.spec_from_file_location('pseudo_releases_plugin', str(plugin_path))
plugin_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin_module)

from constants import (
    OPT_AUTO_SUPPLEMENT,
    OPT_ENABLE_ORIGINAL_COVER_ART,
    OPT_PRESERVE_EXISTING_TAGS,
    OPT_SET_ORIGINAL_RELEASE_ID,
    OPT_SHOW_CONTEXT_MENU,
    PSEUDO_RELEASE_STATUS,
    TAG_ORIGINAL_RELEASE_ID,
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
        self.load_calls = []

    def _finalize_loading(self, error):
        self._finalized = True

    def load(self, **kwargs):
        self.load_calls.append(kwargs)
        self.metadata = MockMetadata()


class MockPluginConfig(dict):
    def register_option(self, name, default):
        if name not in self:
            self[name] = default


class MockPluginApi:
    def __init__(self):
        self.plugin_config = MockPluginConfig({
            OPT_AUTO_SUPPLEMENT: True,
        })
        self.tagger = SimpleNamespace(window=SimpleNamespace(selected_objects=[]))
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


class TestPluginLifecycle(unittest.TestCase):
    def setUp(self):
        self.api = MockPluginApi()
        plugin_module.enable(self.api)

    def test_enable_registers_extension_points(self):
        self.assertEqual(len(self.api.processors), 1)
        self.assertEqual(len(self.api.album_actions), 1)
        self.assertTrue(len(self.api.removal_processors) > 0)
        self.assertTrue(len(self.api.providers) > 0)
        self.assertTrue(len(self.api.options_pages) > 0)

        # Verify options registration
        cfg = self.api.plugin_config
        self.assertTrue(cfg[OPT_AUTO_SUPPLEMENT])
        self.assertFalse(cfg[OPT_PRESERVE_EXISTING_TAGS])
        self.assertTrue(cfg[OPT_SET_ORIGINAL_RELEASE_ID])
        self.assertTrue(cfg[OPT_ENABLE_ORIGINAL_COVER_ART])
        self.assertTrue(cfg[OPT_SHOW_CONTEXT_MENU])

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
        self.assertEqual(self.api.metadata_at_task_add, "orig-1")

        # Assert metadata supplementation succeeded
        self.assertEqual(pseudo_album.metadata["barcode"], "4988008610134")
        self.assertEqual(pseudo_album.metadata["date"], "2001-07-18")
        self.assertEqual(pseudo_album.metadata["releasecountry"], "JP")
        self.assertEqual(pseudo_album.metadata["label"], "Tokuma")
        self.assertEqual(pseudo_album.metadata[TAG_ORIGINAL_RELEASE_ID], "orig-1")

        # Assert finalization kick was triggered
        self.assertTrue(pseudo_album._finalized)

    def test_remove_album_cleans_up_in_flight(self):
        plugin_module.PseudoReleasePlugin.in_flight_albums.add("album-to-remove")
        dummy_album = MockAlbum("album-to-remove")

        plugin_module.PseudoReleasePlugin.remove_album(self.api, dummy_album)
        self.assertNotIn("album-to-remove", plugin_module.PseudoReleasePlugin.in_flight_albums)

    def test_official_release_is_not_modified(self):
        album = MockAlbum("official-1", "Original release")
        release_node = {
            "id": "official-1",
            "status": "Official",
            "relations": [],
        }

        plugin_module.PseudoReleasePlugin.process_album_metadata(
            self.api, album, album.metadata, release_node
        )

        self.assertEqual(album.metadata["album"], "Original release")
        self.assertEqual(self.api.added_tasks, [])

    def test_choose_linked_original_fetches_details_and_reloads_selected_source(self):
        album = MockAlbum("pseudo-1", "Translated soundtrack", status="Pseudo-Release")
        album.metadata["musicbrainz_albumid"] = "pseudo-1"
        album._pseudo_original_candidates = [
            {"id": "original-1", "title": "Original edition A"},
            {"id": "original-2", "title": "Original edition B"},
        ]
        details = {
            "original-1": {
                "id": "original-1",
                "title": "Original edition A",
                "date": "2008-12-24",
                "country": "JP",
                "barcode": "111",
                "packaging": "Jewel Case",
                "disambiguation": "First pressing",
                "media": [
                    {"format": "CD", "track-count": 30},
                    {"format": "CD", "track-count": 25},
                ],
                "label-info": [{"label": {"name": "Square Enix"}, "catalog-number": "SQEX-10130"}],
            },
            "original-2": {
                "id": "original-2",
                "title": "Original edition B",
                "date": "2008-12-24",
                "country": "JP",
                "barcode": "222",
                "media": [
                    {"format": "CD", "track-count": 30},
                    {"format": "CD", "track-count": 25},
                ],
                "label-info": [{"label": {"name": "Square Enix"}, "catalog-number": "SQEX-10132"}],
            },
        }

        album._pseudo_original_details = details
        self.api.tagger.window.selected_objects = [album]
        action = self.api.album_actions[0]()
        shown_menu = action.menu()
        tooltips_vis = shown_menu.toolTipsVisible() if hasattr(shown_menu, 'toolTipsVisible') else shown_menu.tooltips_visible
        self.assertTrue(tooltips_vis)
        raw_actions = shown_menu.actions() if callable(shown_menu.actions) else shown_menu.actions
        real_actions = [entry for entry in raw_actions if entry is not None]
        self.assertEqual(len(real_actions), 3)
        self.assertEqual(real_actions[0].text() if callable(real_actions[0].text) else real_actions[0].text, "Tracks / Year / Country / Format / Label / Cat No")
        texts = [entry.text() if callable(entry.text) else entry.text for entry in real_actions]
        self.assertNotIn("Automatic best match", texts)
        is_enabled = real_actions[0].isEnabled() if hasattr(real_actions[0], 'isEnabled') else real_actions[0].enabled
        self.assertFalse(is_enabled)
        self.assertTrue(real_actions[0].font().bold())
        self.assertFalse(real_actions[0].font().underline())
        self.assertIn("30+25 / 2008 / JP / 2×CD / Square Enix / SQEX-10130", texts[1])
        self.assertIn("30+25 / 2008 / JP / 2×CD / Square Enix / SQEX-10132", texts[2])
        tip1 = real_actions[1].toolTip() if hasattr(real_actions[1], 'toolTip') else getattr(real_actions[1], 'tooltip', '')
        self.assertIn("Packaging: Jewel Case", tip1)
        self.assertIn("Barcode: 111", tip1)
        self.assertIn("Disambiguation: First pressing", tip1)
        is_checked1 = real_actions[1].isChecked() if hasattr(real_actions[1], 'isChecked') else real_actions[1].checked
        is_checked2 = real_actions[2].isChecked() if hasattr(real_actions[2], 'isChecked') else real_actions[2].checked
        self.assertFalse(is_checked1)
        self.assertFalse(is_checked2)
        self.assertEqual(self.api.mb_api.get_release_by_id.call_count, 0)

        real_actions[2].trigger()
        self.assertEqual(album._pseudo_original_release_choice, "original-2")
        self.assertEqual(album._pseudo_original_selection_mode, "manual")
        self.assertEqual(album.load_calls, [{"priority": True, "refresh": True}])
        album.metadata = MockMetadata(
            {
                "releasestatus": "pseudo-release",
                TAG_ORIGINAL_RELEASE_ID: "original-2",
            }
        )
        reopened_menu = self.api.album_actions[0]().menu()
        reopened_raw = reopened_menu.actions() if callable(reopened_menu.actions) else reopened_menu.actions
        reopened_real = [entry for entry in reopened_raw if entry is not None]
        reopened_checked2 = reopened_real[2].isChecked() if hasattr(reopened_real[2], 'isChecked') else reopened_real[2].checked
        self.assertTrue(reopened_checked2)
        self.assertEqual(self.api.mb_api.get_release_by_id.call_count, 0)

    def test_manual_original_choice_overrides_auto_supplement_and_ranking(self):
        self.api.plugin_config[OPT_AUTO_SUPPLEMENT] = False
        album = MockAlbum("pseudo-2", "Translated soundtrack", status="Pseudo-Release")
        album._pseudo_original_source_id = "pseudo-2"
        album._pseudo_original_selection_mode = "manual"
        album._pseudo_original_release_choice = "original-2"
        album._pseudo_original_details = {
            "original-2": {
                "id": "original-2",
                "barcode": "barcode-original-2",
                "media": [],
            }
        }
        release_node = {
            "id": "pseudo-2",
            "status": "Pseudo-Release",
            "relations": [
                {
                    "type": "transl-tracklisting",
                    "direction": "backward",
                    "release": {"id": "original-1", "title": "Edition A"},
                },
                {
                    "type": "transl-tracklisting",
                    "direction": "backward",
                    "release": {"id": "original-2", "title": "Edition B"},
                },
            ],
        }

        def mock_get_release(release_id, callback, inc=None):
            callback(
                {"id": release_id, "barcode": f"barcode-{release_id}", "media": []},
                None,
                None,
            )

        self.api.mb_api.get_release_by_id.side_effect = mock_get_release
        plugin_module.PseudoReleasePlugin.process_album_metadata(
            self.api, album, album.metadata, release_node
        )

        self.assertEqual(self.api.added_tasks, [])
        self.assertEqual(album.metadata["barcode"], "barcode-original-2")
        self.assertEqual(set(album._pseudo_original_details), {"original-1", "original-2"})
        self.assertEqual(self.api.mb_api.get_release_by_id.call_count, 1)

    def test_choose_linked_original_action_disabled_when_option_is_false(self):
        album = MockAlbum("pseudo-1", "Translated soundtrack", status="Pseudo-Release")
        self.api.tagger.window.selected_objects = [album]

        # Case 1: show_linked_editions_menu is False
        self.api.plugin_config[OPT_SHOW_CONTEXT_MENU] = False
        action = plugin_module.ChooseLinkedOriginalAction()
        self.assertFalse(action.isEnabled())

        # Case 2: show_linked_editions_menu is True, but master toggle auto_supplement_pseudo is False
        self.api.plugin_config[OPT_SHOW_CONTEXT_MENU] = True
        self.api.plugin_config[OPT_AUTO_SUPPLEMENT] = False
        action2 = plugin_module.ChooseLinkedOriginalAction()
        self.assertFalse(action2.isEnabled())

    def test_middle_click_and_right_click_open_browser(self):
        """Test middle-click and right-click on linked edition action opens release in browser."""
        album = MockAlbum("pseudo-1", "Translated soundtrack", status="Pseudo-Release")
        album._pseudo_original_candidates = [
            {"id": "orig-mbid-1", "title": "Orig 1", "media": []},
            {"id": "orig-mbid-2", "title": "Orig 2", "media": []},
        ]
        mock_file_lookup = MagicMock()
        self.api.tagger.get_file_lookup = MagicMock(return_value=mock_file_lookup)
        self.api.tagger.window.selected_objects = [album]

        action_instance = plugin_module.ChooseLinkedOriginalAction()
        menu = action_instance.menu()
        self.assertIsNotNone(menu)

        raw_actions = menu.actions() if callable(menu.actions) else menu.actions
        actions = [a for a in raw_actions if a is not None]
        target_action = actions[1]  # first edition candidate
        self.assertEqual(target_action.data(), "orig-mbid-1")

        # Mock actionAt on menu for the eventFilter
        menu.actionAt = MagicMock(return_value=target_action)

        event_middle = SimpleNamespace(
            type=lambda: plugin_module.QtCore.QEvent.Type.MouseButtonRelease,
            button=lambda: plugin_module.QtCore.Qt.MouseButton.MiddleButton,
            pos=lambda: None,
        )
        filt = action_instance._menu_filter
        handled = filt.eventFilter(menu, event_middle)
        self.assertTrue(handled)
        mock_file_lookup.album_lookup.assert_called_with("orig-mbid-1")

        # Simulate event filter receiving RightButton release for the second candidate
        menu.actionAt = MagicMock(return_value=actions[2])
        event_right = SimpleNamespace(
            type=lambda: plugin_module.QtCore.QEvent.Type.MouseButtonRelease,
            button=lambda: plugin_module.QtCore.Qt.MouseButton.RightButton,
            pos=lambda: None,
        )
        handled_right = filt.eventFilter(menu, event_right)
        self.assertTrue(handled_right)
        mock_file_lookup.album_lookup.assert_called_with("orig-mbid-2")


if __name__ == '__main__':
    unittest.main()
