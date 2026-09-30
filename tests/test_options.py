# Tests for plugin options page load/save logic
import unittest
from options import PseudoReleaseOptionsPage
from constants import (
    OPT_AUTO_OVERLAY,
    OPT_AUTO_SUPPLEMENT,
    OPT_ENABLED,
    OPT_SKIP_LATIN_ORIGINALS,
    OPT_TARGET_SCRIPT_MODE,
    SCRIPT_MODE_ENG,
    SCRIPT_MODE_LATN,
    SCRIPT_MODE_LOCALES,
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
                OPT_AUTO_OVERLAY: False,
                OPT_TARGET_SCRIPT_MODE: SCRIPT_MODE_ENG,
                OPT_SKIP_LATIN_ORIGINALS: False,
            }
        )
        page.api = api

        # Load into UI
        page.load()
        self.assertTrue(page.cb_enabled.isChecked())
        self.assertTrue(page.cb_auto_supplement.isChecked())
        self.assertFalse(page.cb_auto_overlay.isChecked())
        self.assertTrue(page.rb_eng.isChecked())
        self.assertFalse(page.rb_latn.isChecked())
        self.assertFalse(page.cb_skip_latin.isChecked())

        # Modify UI
        page.cb_auto_overlay.setChecked(True)
        page.rb_eng.setChecked(False)
        page.rb_locales.setChecked(True)
        page.cb_skip_latin.setChecked(True)

        # Save from UI
        page.save()
        self.assertTrue(api.plugin_config[OPT_AUTO_OVERLAY])
        self.assertEqual(api.plugin_config[OPT_TARGET_SCRIPT_MODE], SCRIPT_MODE_LOCALES)
        self.assertTrue(api.plugin_config[OPT_SKIP_LATIN_ORIGINALS])

    def test_profile_config_section_without_get(self):
        """Verify load() and save() work on ProfileConfigSection which has NO .get() method."""
        page = PseudoReleaseOptionsPage()
        section = ProfileConfigSectionMock({
            OPT_ENABLED: True,
            OPT_AUTO_SUPPLEMENT: False,
            OPT_AUTO_OVERLAY: True,
            OPT_TARGET_SCRIPT_MODE: SCRIPT_MODE_LOCALES,
            OPT_SKIP_LATIN_ORIGINALS: True,
        })
        self.assertFalse(hasattr(section, 'get'))

        class ApiWithSection:
            plugin_config = section

        page.api = ApiWithSection()
        # Should not raise AttributeError: 'ProfileConfigSection' object has no attribute 'get'
        page.load()
        self.assertTrue(page.cb_enabled.isChecked())
        self.assertFalse(page.cb_auto_supplement.isChecked())
        self.assertTrue(page.cb_auto_overlay.isChecked())
        self.assertTrue(page.rb_locales.isChecked())
        self.assertTrue(page.cb_skip_latin.isChecked())

    def test_save_latn_mode(self):
        page = PseudoReleaseOptionsPage()
        api = MockPluginApi({})
        page.api = api
        page.rb_latn.setChecked(True)
        page.rb_eng.setChecked(False)
        page.rb_locales.setChecked(False)
        page.save()
        self.assertEqual(api.plugin_config[OPT_TARGET_SCRIPT_MODE], SCRIPT_MODE_LATN)


if __name__ == '__main__':
    unittest.main()
