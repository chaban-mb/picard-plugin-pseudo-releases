# Tests for plugin options page load/save logic
import unittest
from options import PseudoReleaseOptionsPage
from constants import (
    OPT_AUTO_SUPPLEMENT,
    OPT_ENABLED,
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
                OPT_ENABLED: True,
                OPT_AUTO_SUPPLEMENT: True,
            }
        )
        page.api = api

        # Load into UI
        page.load()
        self.assertTrue(page.cb_enabled.isChecked())
        self.assertTrue(page.cb_auto_supplement.isChecked())

        # Modify UI
        page.cb_auto_supplement.setChecked(False)

        # Save from UI
        page.save()
        self.assertFalse(api.plugin_config[OPT_AUTO_SUPPLEMENT])

    def test_inline_descriptions_explain_supplement_and_overlay(self):
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
        self.assertIn("missing tags only", supplement_description)
        self.assertIn("Cover art", supplement_description)

    def test_dependent_controls_follow_feature_toggles(self):
        page = PseudoReleaseOptionsPage()
        api = MockPluginApi(
            {
                OPT_ENABLED: False,
                OPT_AUTO_SUPPLEMENT: True,
            }
        )
        page.api = api
        page.load()

        self.assertFalse(page.cb_auto_supplement.isEnabled())
        self.assertTrue(page.cb_auto_supplement.isChecked())

        page.cb_enabled.setChecked(True)
        self.assertTrue(page.cb_auto_supplement.isEnabled())

    def test_profile_config_section_without_get(self):
        """Verify load() and save() work on ProfileConfigSection which has NO .get() method."""
        page = PseudoReleaseOptionsPage()
        section = ProfileConfigSectionMock({
            OPT_ENABLED: True,
            OPT_AUTO_SUPPLEMENT: False,
        })
        self.assertFalse(hasattr(section, 'get'))

        class ApiWithSection:
            plugin_config = section

        page.api = ApiWithSection()
        # Should not raise AttributeError: 'ProfileConfigSection' object has no attribute 'get'
        page.load()
        self.assertTrue(page.cb_enabled.isChecked())
        self.assertFalse(page.cb_auto_supplement.isChecked())


if __name__ == '__main__':
    unittest.main()
