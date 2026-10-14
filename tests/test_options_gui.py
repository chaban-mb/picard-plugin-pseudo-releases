"""In-process GUI tests using pytest-qt and QTest for PseudoReleaseOptionsPage."""

import os
import pytest
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from pseudo_releases.options import PseudoReleaseOptionsPage


from tests.mocks.mock_picard import MockPluginApi


@pytest.fixture(autouse=True)
def ensure_offscreen():
    """Ensure offscreen platform to guarantee headless execution."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_options_page_widgets_instantiation(qtbot):
    """Test that all Qt widgets, group boxes, and layouts instantiate correctly."""
    page = PseudoReleaseOptionsPage()
    qtbot.addWidget(page)

    assert isinstance(page.group_cover_art, QtWidgets.QGroupBox)
    assert isinstance(page.btn_open_cover_providers, QtWidgets.QPushButton)

    assert page.lbl_info.wordWrap()
    assert page.lbl_info.openExternalLinks()
    assert page.lbl_cover_art_description.wordWrap()
    assert page.lbl_cover_art_note.wordWrap()


def test_open_cover_providers_click(qtbot):
    """Test clicking Open Cover Art Providers invokes navigation without error."""
    page = PseudoReleaseOptionsPage()
    qtbot.addWidget(page)

    class MockPagesTree:
        def __init__(self):
            self.current_item = None

        def setCurrentItem(self, item):
            self.current_item = item

    class MockDialog:
        def __init__(self):
            self.ui = type('UI', (), {'pages_tree': MockPagesTree()})()
            self.pagename_to_item = {'cover': 'item-cover-art'}

    mock_dialog = MockDialog()
    page.dialog = mock_dialog

    QTest.mouseClick(page.btn_open_cover_providers, Qt.MouseButton.LeftButton)
    assert mock_dialog.ui.pages_tree.current_item == 'item-cover-art'


def test_load_and_save_without_error(qtbot):
    """Verify loading and saving on plugin configuration."""
    page = PseudoReleaseOptionsPage()
    qtbot.addWidget(page)
    page.api = MockPluginApi()
    page.load()
    page.save()


