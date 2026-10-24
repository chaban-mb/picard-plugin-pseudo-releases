# Tests for PseudoReleaseOptionsPage widget, navigation, and configuration
import unittest

from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from pseudo_releases.options import PseudoReleaseOptionsPage
from tests.mocks.mock_picard import MockPluginApi


class TestOptionsPage(unittest.TestCase):
    def test_options_page_metadata(self):
        self.assertIn(PseudoReleaseOptionsPage.TITLE, {"options.title", "Pseudo-Releases"})
        self.assertEqual(PseudoReleaseOptionsPage.NAME, "pseudo_releases")
        self.assertEqual(PseudoReleaseOptionsPage.PARENT, "plugins")
        self.assertEqual(PseudoReleaseOptionsPage.OPTIONS, {})

    def test_widgets_and_descriptions(self):
        page = PseudoReleaseOptionsPage()

        self.assertIsInstance(page.group_cover_art, QtWidgets.QGroupBox)
        self.assertIsInstance(page.btn_open_cover_providers, QtWidgets.QPushButton)
        self.assertTrue(page.lbl_info.wordWrap())
        self.assertTrue(page.lbl_info.openExternalLinks())
        self.assertTrue(page.lbl_cover_art_description.wordWrap())
        self.assertTrue(page.lbl_cover_art_note.wordWrap())

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

        self.assertIn(
            "https://musicbrainz.org/doc/Style/Specific_types_of_releases/Pseudo-Releases",
            info_description,
        )
        self.assertIn(
            "https://musicbrainz.org/relationship/fc399d47-23a7-4c28-bfcf-0607a562b644",
            info_description,
        )
        self.assertIn("Options > Cover Art > Providers", page.lbl_cover_art_note.text())

    def test_open_cover_providers_click(self):
        page = PseudoReleaseOptionsPage()

        class MockPagesTree:
            def __init__(self):
                self.current_item = None

            def setCurrentItem(self, item):
                self.current_item = item

        class MockDialog:
            def __init__(self):
                self.ui = type("UI", (), {"pages_tree": MockPagesTree()})()
                self.pagename_to_item = {"cover": "item-cover-art"}

        mock_dialog = MockDialog()
        page.dialog = mock_dialog

        QTest.mouseClick(page.btn_open_cover_providers, Qt.MouseButton.LeftButton)
        self.assertEqual(mock_dialog.ui.pages_tree.current_item, "item-cover-art")

    def test_load_and_save_options(self):
        page = PseudoReleaseOptionsPage()
        page.api = MockPluginApi({})
        page.load()
        page.save()


if __name__ == "__main__":
    unittest.main()
