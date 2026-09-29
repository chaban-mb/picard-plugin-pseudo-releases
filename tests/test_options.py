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


class TestOptionsPage(unittest.TestCase):
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
