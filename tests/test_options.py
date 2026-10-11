# Tests for plugin options page load/save logic
import unittest
from options import PseudoReleaseOptionsPage


class MockPluginApi:
    def __init__(self, initial_config=None):
        self.plugin_config = initial_config or {}


class TestOptionsPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from PyQt6.QtWidgets import QApplication
            cls.app = QApplication.instance()
        except ImportError:
            cls.app = None

    def test_options_page_metadata(self):
        self.assertEqual(PseudoReleaseOptionsPage.TITLE, "Pseudo-Releases")
        self.assertEqual(PseudoReleaseOptionsPage.NAME, "pseudo_releases")
        self.assertEqual(PseudoReleaseOptionsPage.PARENT, "plugins")
        self.assertEqual(PseudoReleaseOptionsPage.OPTIONS, {})

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
        api = MockPluginApi({})
        page.api = api

        # Load and save operate cleanly without raising exceptions
        page.load()
        page.save()

    def test_ui_descriptions_and_groups(self):
        page = PseudoReleaseOptionsPage()

        info_description = page.lbl_info.text()
        for tag in (
            "date",
            "releasecountry",
            "barcode",
            "media",
            "label",
            "catalognumber",
            "%_original_musicbrainz_albumid%",
        ):
            self.assertIn(tag, info_description)

        # External doc links
        self.assertIn("https://musicbrainz.org/doc/Style/Specific_types_of_releases/Pseudo-Releases", info_description)
        self.assertIn("https://musicbrainz.org/relationship/fc399d47-23a7-4c28-bfcf-0607a562b644", info_description)

        self.assertIn("Cover Art", page.group_cover_art.title())
        self.assertIn("Cover Art Archive", page.lbl_cover_art_description.text())
        self.assertIn("Options &gt; Cover Art &gt; Providers", page.lbl_cover_art_note.text())
        self.assertTrue(hasattr(page, "btn_open_cover_providers"))


if __name__ == '__main__':
    unittest.main()
