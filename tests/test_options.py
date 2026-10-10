# Tests for plugin options page load/save logic
import unittest
from options import PseudoReleaseOptionsPage
from constants import (
    OPT_AUTO_SUPPLEMENT,
    OPT_ENABLE_ORIGINAL_COVER_ART,
    OPT_PRESERVE_EXISTING_TAGS,
    OPT_SET_ORIGINAL_RELEASE_ID,
    OPT_SHOW_CONTEXT_MENU,
)


class MockPluginApi:
    def __init__(self, initial_config=None):
        self.plugin_config = initial_config or {}


class ProfileConfigSectionMock:
    """Mock simulating Picard's ProfileConfigSection which lacks .get() method."""

    def __init__(self, initial=None):
        self._data = dict(initial or {})

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __contains__(self, key):
        return key in self._data


class TestOptionsPage(unittest.TestCase):
    def test_options_page_metadata(self):
        self.assertEqual(PseudoReleaseOptionsPage.TITLE, "Pseudo-Releases")
        self.assertEqual(PseudoReleaseOptionsPage.NAME, "pseudo_releases")
        self.assertEqual(PseudoReleaseOptionsPage.PARENT, "plugins")
        self.assertIn(OPT_AUTO_SUPPLEMENT, PseudoReleaseOptionsPage.OPTIONS)
        self.assertIn(OPT_PRESERVE_EXISTING_TAGS, PseudoReleaseOptionsPage.OPTIONS)
        self.assertIn(OPT_SET_ORIGINAL_RELEASE_ID, PseudoReleaseOptionsPage.OPTIONS)
        self.assertIn(OPT_ENABLE_ORIGINAL_COVER_ART, PseudoReleaseOptionsPage.OPTIONS)
        self.assertIn(OPT_SHOW_CONTEXT_MENU, PseudoReleaseOptionsPage.OPTIONS)

    def test_tr_helper(self):
        page = PseudoReleaseOptionsPage()
        # Without api attached, returns default English text
        self.assertEqual(page._tr("ui.some_key", "Fallback Text"), "Fallback Text")

        # With api attached and tr available
        class MockApiWithTr:
            def tr(self, key, default):
                if key == "ui.custom":
                    return "Übersetzt"
                return default

        page.api = MockApiWithTr()
        self.assertEqual(page._tr("ui.custom", "Default"), "Übersetzt")
        self.assertEqual(page._tr("ui.missing", "Default"), "Default")

    def test_load_and_save_options(self):
        page = PseudoReleaseOptionsPage()
        api = MockPluginApi(
            {
                OPT_AUTO_SUPPLEMENT: True,
                OPT_PRESERVE_EXISTING_TAGS: False,
                OPT_SET_ORIGINAL_RELEASE_ID: True,
                OPT_ENABLE_ORIGINAL_COVER_ART: True,
                OPT_SHOW_CONTEXT_MENU: True,
            }
        )
        page.api = api

        # Load into UI
        page.load()
        self.assertTrue(page.cb_auto_supplement.isChecked())
        self.assertFalse(page.cb_preserve_existing.isChecked())
        self.assertTrue(page.cb_set_original_tag.isChecked())
        self.assertTrue(page.cb_enable_original_cover_art.isChecked())
        self.assertTrue(page.cb_show_context_menu.isChecked())

        # Modify UI
        page.cb_auto_supplement.setChecked(False)
        page.cb_preserve_existing.setChecked(True)
        page.cb_set_original_tag.setChecked(False)
        page.cb_enable_original_cover_art.setChecked(False)
        page.cb_show_context_menu.setChecked(False)

        # Save from UI
        page.save()
        self.assertFalse(api.plugin_config[OPT_AUTO_SUPPLEMENT])
        self.assertTrue(api.plugin_config[OPT_PRESERVE_EXISTING_TAGS])
        self.assertFalse(api.plugin_config[OPT_SET_ORIGINAL_RELEASE_ID])
        self.assertFalse(api.plugin_config[OPT_ENABLE_ORIGINAL_COVER_ART])
        self.assertFalse(api.plugin_config[OPT_SHOW_CONTEXT_MENU])

    def test_defaults_when_empty_config(self):
        page = PseudoReleaseOptionsPage()
        page.api = MockPluginApi({})
        page.load()

        # preserve_existing_tags defaults to False, others default to True
        self.assertTrue(page.cb_auto_supplement.isChecked())
        self.assertFalse(page.cb_preserve_existing.isChecked())
        self.assertTrue(page.cb_set_original_tag.isChecked())
        self.assertTrue(page.cb_enable_original_cover_art.isChecked())
        self.assertTrue(page.cb_show_context_menu.isChecked())

    def test_master_toggle_cascading_disables_dependent_options(self):
        page = PseudoReleaseOptionsPage()
        page.api = MockPluginApi({OPT_AUTO_SUPPLEMENT: True})
        page.load()

        self.assertTrue(page.cb_preserve_existing.isEnabled())
        self.assertTrue(page.cb_set_original_tag.isEnabled())
        self.assertTrue(page.cb_enable_original_cover_art.isEnabled())
        self.assertTrue(page.cb_show_context_menu.isEnabled())

        # Uncheck master toggle
        page.cb_auto_supplement.setChecked(False)
        self.assertFalse(page.cb_preserve_existing.isEnabled())
        self.assertFalse(page.cb_set_original_tag.isEnabled())
        self.assertFalse(page.cb_enable_original_cover_art.isEnabled())
        self.assertFalse(page.cb_show_context_menu.isEnabled())

        # Re-check master toggle
        page.cb_auto_supplement.setChecked(True)
        self.assertTrue(page.cb_preserve_existing.isEnabled())
        self.assertTrue(page.cb_set_original_tag.isEnabled())
        self.assertTrue(page.cb_enable_original_cover_art.isEnabled())
        self.assertTrue(page.cb_show_context_menu.isEnabled())

    def test_ui_descriptions_and_groups(self):
        page = PseudoReleaseOptionsPage()

        supplement_description = page.lbl_auto_supplement_description.text()
        for tag in (
            "date",
            "originaldate",
            "releasecountry",
            "barcode",
            "media",
            "label",
            "catalognumber",
        ):
            self.assertIn(tag, supplement_description)

        self.assertIn("~original_musicbrainz_albumid", page.cb_set_original_tag.text())
        self.assertIn("Cover Art", page.group_cover_art.text())
        self.assertIn("Linked Original Editions", page.group_context_menu.text())

    def test_profile_config_section_without_get(self):
        """Verify load() and save() work on ProfileConfigSection which has NO .get() method."""
        page = PseudoReleaseOptionsPage()
        section = ProfileConfigSectionMock({
            OPT_AUTO_SUPPLEMENT: False,
            OPT_PRESERVE_EXISTING_TAGS: True,
            OPT_SET_ORIGINAL_RELEASE_ID: False,
            OPT_ENABLE_ORIGINAL_COVER_ART: False,
            OPT_SHOW_CONTEXT_MENU: False,
        })
        self.assertFalse(hasattr(section, 'get'))

        class ApiWithSection:
            plugin_config = section

        page.api = ApiWithSection()
        page.load()
        self.assertFalse(page.cb_auto_supplement.isChecked())
        self.assertTrue(page.cb_preserve_existing.isChecked())
        self.assertFalse(page.cb_set_original_tag.isChecked())
        self.assertFalse(page.cb_enable_original_cover_art.isChecked())
        self.assertFalse(page.cb_show_context_menu.isChecked())


if __name__ == '__main__':
    unittest.main()
