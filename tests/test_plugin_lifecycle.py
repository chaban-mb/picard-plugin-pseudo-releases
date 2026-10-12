# Integration tests for plugin lifecycle, task queues, and processor integration
import unittest
from unittest.mock import MagicMock
import importlib.util
from pathlib import Path
from types import SimpleNamespace

from PyQt6 import QtCore

plugin_path = Path(__file__).resolve().parent.parent / '__init__.py'
spec = importlib.util.spec_from_file_location('pseudo_releases_plugin', str(plugin_path))
plugin_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin_module)

from constants import (
    PSEUDO_RELEASE_STATUS,
    TAG_ORIGINAL_RELEASE_ID,
)


from tests.mocks.mock_picard import (
    MockAlbum,
    MockMetadata,
    MockPluginApi,
    MockPluginConfig,
)


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
        self.assertTrue(any(v[0] == "_original_musicbrainz_albumid" for v in self.api.script_variables))

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
        def mock_get_release(rel_id, callback, inc=None, **kwargs):
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
        self.assertEqual(self.api.metadata_at_task_add, "")
        self.assertEqual(pseudo_album._pseudo_original_id, "orig-1")

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
        self.assertTrue(shown_menu.toolTipsVisible())
        raw_actions = shown_menu.actions()
        real_actions = [entry for entry in raw_actions if entry is not None]
        self.assertEqual(len(real_actions), 3)
        self.assertEqual(real_actions[0].text(), "Tracks / Year / Country / Format / Label / Cat No")
        texts = [entry.text() for entry in real_actions]
        self.assertNotIn("Automatic best match", texts)
        self.assertFalse(real_actions[0].isEnabled())
        self.assertTrue(real_actions[0].font().bold())
        self.assertFalse(real_actions[0].font().underline())
        self.assertIn("30+25 / 2008 / JP / 2×CD / Square Enix / SQEX-10130", texts[1])
        self.assertIn("30+25 / 2008 / JP / 2×CD / Square Enix / SQEX-10132", texts[2])
        tip1 = real_actions[1].toolTip()
        self.assertIn("Packaging: Jewel Case", tip1)
        self.assertIn("Barcode: 111", tip1)
        self.assertIn("Disambiguation: First pressing", tip1)
        self.assertFalse(real_actions[1].isChecked())
        self.assertFalse(real_actions[2].isChecked())
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
        reopened_raw = reopened_menu.actions()
        reopened_real = [entry for entry in reopened_raw if entry is not None]
        self.assertTrue(reopened_real[2].isChecked())
        self.assertEqual(self.api.mb_api.get_release_by_id.call_count, 0)

    def test_manual_original_choice_overrides_auto_supplement_and_ranking(self):
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
        album._pseudo_original_is_full = {"original-2": True}
        album._pseudo_candidate_stubs = {"original-1": {"id": "original-1"}}
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

        plugin_module.PseudoReleasePlugin.process_album_metadata(
            self.api, album, album.metadata, release_node
        )

        self.assertEqual(self.api.added_tasks, [])
        self.assertEqual(album.metadata["barcode"], "barcode-original-2")
        self.assertEqual(album._pseudo_original_details["original-2"]["barcode"], "barcode-original-2")

    def test_choose_linked_original_action_disabled_when_not_single_pseudo_album(self):
        album = MockAlbum("normal-1", "Standard soundtrack", status="Official")
        self.api.tagger.window.selected_objects = [album]

        action = plugin_module.ChooseLinkedOriginalAction()
        self.assertFalse(action.isEnabled())

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
            type=lambda: QtCore.QEvent.Type.MouseButtonRelease,
            button=lambda: QtCore.Qt.MouseButton.MiddleButton,
            pos=lambda: None,
        )
        filt = action_instance._menu_filter
        handled = filt.eventFilter(menu, event_middle)
        self.assertTrue(handled)
        mock_file_lookup.album_lookup.assert_called_with("orig-mbid-1")

        # Simulate event filter receiving RightButton release for the second candidate
        menu.actionAt = MagicMock(return_value=actions[2])
        event_right = SimpleNamespace(
            type=lambda: QtCore.QEvent.Type.MouseButtonRelease,
            button=lambda: QtCore.Qt.MouseButton.RightButton,
            pos=lambda: None,
        )
        handled_right = filt.eventFilter(menu, event_right)
        self.assertTrue(handled_right)
        mock_file_lookup.album_lookup.assert_called_with("orig-mbid-2")

    def test_enable_registers_cover_art_provider(self):
        self.assertIn(plugin_module.PseudoReleaseCoverArtProvider, self.api.providers)

    def test_enrichment_request_uses_mblogin_when_authorized(self):
        pseudo_album = MockAlbum("pseudo-1", title="Title", status="Pseudo-Release")
        pseudo_node = {
            "id": "pseudo-1",
            "status": "Pseudo-Release",
            "relations": [
                {
                    "type": "transl-tracklisting",
                    "direction": "backward",
                    "release": {"id": "orig-auth", "status": "Official"},
                }
            ],
        }

        mock_oauth = MagicMock()
        mock_oauth.is_authorized.return_value = True
        self.api.tagger = SimpleNamespace(
            webservice=SimpleNamespace(oauth_manager=mock_oauth)
        )

        captured_kwargs = {}

        def mock_get_release(rel_id, callback, **kwargs):
            captured_kwargs.update(kwargs)
            callback({"id": rel_id}, None, None)

        self.api.mb_api.get_release_by_id.side_effect = mock_get_release

        mock_cfg = SimpleNamespace(
            setting={
                "release_ars": False,
                "use_genres": True,
                "only_my_genres": True,
            }
        )

        with unittest.mock.patch("metadata_engine.config", mock_cfg):
            plugin_module.PseudoReleasePlugin.process_album_metadata(
                api=self.api,
                album=pseudo_album,
                album_metadata=pseudo_album.metadata,
                release_node=pseudo_node,
            )

        self.assertTrue(captured_kwargs.get("mblogin"))

    def test_enrichment_request_falls_back_when_not_authorized(self):
        pseudo_album = MockAlbum("pseudo-2", title="Title", status="Pseudo-Release")
        pseudo_node = {
            "id": "pseudo-2",
            "status": "Pseudo-Release",
            "relations": [
                {
                    "type": "transl-tracklisting",
                    "direction": "backward",
                    "release": {"id": "orig-unauth", "status": "Official"},
                }
            ],
        }

        # User is not logged in / not authorized
        mock_oauth = MagicMock()
        mock_oauth.is_authorized.return_value = False
        self.api.tagger = SimpleNamespace(
            webservice=SimpleNamespace(oauth_manager=mock_oauth)
        )

        captured_kwargs = {}

        def mock_get_release(rel_id, callback, **kwargs):
            captured_kwargs.update(kwargs)
            callback({"id": rel_id}, None, None)

        self.api.mb_api.get_release_by_id.side_effect = mock_get_release

        # Configure only_my_genres on global config
        mock_cfg = SimpleNamespace(
            setting={
                "release_ars": False,
                "use_genres": True,
                "only_my_genres": True,
            }
        )

        with unittest.mock.patch("metadata_engine.config", mock_cfg):
            plugin_module.PseudoReleasePlugin.process_album_metadata(
                api=self.api,
                album=pseudo_album,
                album_metadata=pseudo_album.metadata,
                release_node=pseudo_node,
            )

        inc = captured_kwargs.get("inc", [])
        self.assertNotIn("user-tags", inc)
        self.assertNotIn("user-genres", inc)
        self.assertIn("tags", inc)
        self.assertIn("genres", inc)

    def test_plugin_tr_helper(self):
        # When api is None
        plugin_module.PseudoReleasePlugin.api = None
        self.assertEqual(
            plugin_module.PseudoReleasePlugin._tr("action.tooltip_open_browser", "Fallback Hint"),
            "Fallback Hint",
        )

        # When api is attached without custom translation
        plugin_module.PseudoReleasePlugin.api = self.api
        self.assertEqual(
            plugin_module.PseudoReleasePlugin._tr("action.tooltip_open_browser", "Fallback Hint"),
            "Fallback Hint",
        )

        # When api returns a translated string
        mock_api = MagicMock()
        mock_api.tr.return_value = "Translated Tooltip Hint"
        plugin_module.PseudoReleasePlugin.api = mock_api
        self.assertEqual(
            plugin_module.PseudoReleasePlugin._tr("action.tooltip_open_browser", "Fallback Hint"),
            "Translated Tooltip Hint",
        )
        mock_api.tr.assert_called_with("action.tooltip_open_browser", "Fallback Hint")

    def test_cancellation_recovery(self):
        """Regression Test [P1]: If Picard aborts an enrichment request without running its callback,
        re-processing the same album heals in_flight_albums and retries enrichment.
        """
        pseudo_album = MockAlbum("pseudo-cancellation-test", "Transliterated Album")
        pseudo_node = {
            "id": "pseudo-cancellation-test",
            "status": "Pseudo-Release",
            "relations": [
                {
                    "type": "transl-tracklisting",
                    "direction": "backward",
                    "target-type": "release",
                    "release": {"id": "orig-cancel-1", "title": "Original Album"},
                }
            ],
        }

        # Step 1: Simulate starting enrichment, but aborted/canceled by Picard
        plugin_module.PseudoReleasePlugin.in_flight_albums.add("pseudo-cancellation-test")
        # Ensure album._pending_tasks has no active pseudo_enrich_ task (aborted externally)
        pseudo_album._pending_tasks.clear()

        # Step 2: User refreshes metadata on the same album without removing it
        retried = False

        def mock_get_release(release_id, callback, **kwargs):
            nonlocal retried
            retried = True
            callback({"id": release_id, "barcode": "1234567890"}, None, None)

        self.api.mb_api.get_release_by_id.side_effect = mock_get_release

        plugin_module.PseudoReleasePlugin.process_album_metadata(
            api=self.api,
            album=pseudo_album,
            album_metadata=pseudo_album.metadata,
            release_node=pseudo_node,
        )

        self.assertTrue(retried, "Enrichment must be retried after request cancellation without removing album")
        self.assertEqual(pseudo_album.metadata["barcode"], "1234567890")

    def test_failed_enrichment_does_not_tag(self):
        """Regression Test [P2]: A failed network request must not write TAG_ORIGINAL_RELEASE_ID,
        preventing future automatic retries from being blocked.
        """
        pseudo_album = MockAlbum("pseudo-error-test", "Transliterated Album")
        pseudo_node = {
            "id": "pseudo-error-test",
            "status": "Pseudo-Release",
            "relations": [
                {
                    "type": "transl-tracklisting",
                    "direction": "backward",
                    "target-type": "release",
                    "release": {"id": "orig-err-1", "title": "Original Album"},
                }
            ],
        }

        # Simulate network error in MB API
        def mock_error_get(release_id, callback, **kwargs):
            callback({}, None, "Network 500 Internal Server Error")

        self.api.mb_api.get_release_by_id.side_effect = mock_error_get

        plugin_module.PseudoReleasePlugin.process_album_metadata(
            api=self.api,
            album=pseudo_album,
            album_metadata=pseudo_album.metadata,
            release_node=pseudo_node,
        )

        # TAG_ORIGINAL_RELEASE_ID must NOT be set on error
        self.assertEqual(pseudo_album.metadata.get(TAG_ORIGINAL_RELEASE_ID), "")
        self.assertNotIn("pseudo-error-test", plugin_module.PseudoReleasePlugin.in_flight_albums)


if __name__ == '__main__':
    unittest.main()

