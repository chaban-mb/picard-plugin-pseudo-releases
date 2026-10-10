"""In-process GUI tests using pytest-qt and QTest for PseudoReleaseOptionsPage."""

import os
import pytest
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from constants import (
    OPT_AUTO_SUPPLEMENT,
    OPT_ENABLE_ORIGINAL_COVER_ART,
    OPT_PRESERVE_EXISTING_TAGS,
    OPT_SET_ORIGINAL_RELEASE_ID,
    OPT_SHOW_CONTEXT_MENU,
)
from options import PseudoReleaseOptionsPage


class MockPluginApi:
    def __init__(self, initial_config=None):
        self.plugin_config = initial_config or {}


@pytest.fixture(autouse=True)
def ensure_offscreen():
    """Ensure offscreen platform to guarantee headless execution."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_options_page_widgets_instantiation(qtbot):
    """Test that all Qt widgets, group boxes, and layouts instantiate correctly."""
    page = PseudoReleaseOptionsPage()
    qtbot.addWidget(page)

    assert isinstance(page.group_metadata, QtWidgets.QGroupBox)
    assert isinstance(page.group_cover_art, QtWidgets.QGroupBox)
    assert isinstance(page.group_context_menu, QtWidgets.QGroupBox)

    assert isinstance(page.cb_auto_supplement, QtWidgets.QCheckBox)
    assert isinstance(page.cb_preserve_existing, QtWidgets.QCheckBox)
    assert isinstance(page.cb_set_original_tag, QtWidgets.QCheckBox)
    assert isinstance(page.cb_enable_original_cover_art, QtWidgets.QCheckBox)
    assert isinstance(page.cb_show_context_menu, QtWidgets.QCheckBox)

    assert page.lbl_info.wordWrap()
    assert page.lbl_auto_supplement_description.wordWrap()
    assert page.lbl_cover_art_description.wordWrap()
    assert page.lbl_context_menu_description.wordWrap()


def test_mouse_click_master_toggle_cascades_disabled_state(qtbot):
    """Test simulating mouse click with QTest on cb_auto_supplement cascades enabled/disabled state."""
    page = PseudoReleaseOptionsPage()
    qtbot.addWidget(page)
    page.api = MockPluginApi({OPT_AUTO_SUPPLEMENT: True})
    page.load()
    page.show()

    # Initially master toggle is checked and sub-options are enabled
    assert page.cb_auto_supplement.isChecked()
    assert page.cb_preserve_existing.isEnabled()
    assert page.cb_set_original_tag.isEnabled()
    assert page.cb_enable_original_cover_art.isEnabled()
    assert page.cb_show_context_menu.isEnabled()

    # Simulate user left-click on master checkbox
    QTest.mouseClick(page.cb_auto_supplement, Qt.MouseButton.LeftButton)

    # Master checkbox is now unchecked, dependent controls must be disabled
    assert not page.cb_auto_supplement.isChecked()
    assert not page.cb_preserve_existing.isEnabled()
    assert not page.cb_set_original_tag.isEnabled()
    assert not page.cb_enable_original_cover_art.isEnabled()
    assert not page.cb_show_context_menu.isEnabled()

    # Click again to re-enable
    QTest.mouseClick(page.cb_auto_supplement, Qt.MouseButton.LeftButton)
    assert page.cb_auto_supplement.isChecked()
    assert page.cb_preserve_existing.isEnabled()
    assert page.cb_set_original_tag.isEnabled()
    assert page.cb_enable_original_cover_art.isEnabled()
    assert page.cb_show_context_menu.isEnabled()


def test_mouse_clicks_on_sub_options(qtbot):
    """Test clicking sub-options toggles their checked states."""
    page = PseudoReleaseOptionsPage()
    qtbot.addWidget(page)
    page.api = MockPluginApi()
    page.load()
    page.show()

    # cb_preserve_existing is False (unchecked) by default
    assert not page.cb_preserve_existing.isChecked()
    QTest.mouseClick(page.cb_preserve_existing, Qt.MouseButton.LeftButton)
    assert page.cb_preserve_existing.isChecked()

    # cb_set_original_tag is True (checked) by default
    assert page.cb_set_original_tag.isChecked()
    QTest.mouseClick(page.cb_set_original_tag, Qt.MouseButton.LeftButton)
    assert not page.cb_set_original_tag.isChecked()

    # Save to config and verify
    page.save()
    assert page.api.plugin_config[OPT_PRESERVE_EXISTING_TAGS] is True
    assert page.api.plugin_config[OPT_SET_ORIGINAL_RELEASE_ID] is False


def test_real_qt_signal_spy(qtbot):
    """Verify Qt signal emissions using qtbot signal watcher."""
    page = PseudoReleaseOptionsPage()
    qtbot.addWidget(page)

    with qtbot.waitSignal(page.cb_auto_supplement.toggled, timeout=1000) as blocker:
        page.cb_auto_supplement.setChecked(True)

    assert blocker.args == [True]


def test_load_and_save_full_roundtrip_with_real_widgets(qtbot):
    """Verify loading from and saving to plugin configuration using real Qt widgets."""
    page = PseudoReleaseOptionsPage()
    qtbot.addWidget(page)

    cfg = {
        OPT_AUTO_SUPPLEMENT: True,
        OPT_PRESERVE_EXISTING_TAGS: False,
        OPT_SET_ORIGINAL_RELEASE_ID: True,
        OPT_ENABLE_ORIGINAL_COVER_ART: True,
        OPT_SHOW_CONTEXT_MENU: True,
    }
    page.api = MockPluginApi(cfg)
    page.load()

    assert page.cb_auto_supplement.isChecked()
    assert not page.cb_preserve_existing.isChecked()
    assert page.cb_set_original_tag.isChecked()
    assert page.cb_enable_original_cover_art.isChecked()
    assert page.cb_show_context_menu.isChecked()

    # Invert all checkboxes programmatically
    page.cb_auto_supplement.setChecked(False)
    page.cb_preserve_existing.setChecked(True)
    page.cb_set_original_tag.setChecked(False)
    page.cb_enable_original_cover_art.setChecked(False)
    page.cb_show_context_menu.setChecked(False)

    page.save()

    assert cfg[OPT_AUTO_SUPPLEMENT] is False
    assert cfg[OPT_PRESERVE_EXISTING_TAGS] is True
    assert cfg[OPT_SET_ORIGINAL_RELEASE_ID] is False
    assert cfg[OPT_ENABLE_ORIGINAL_COVER_ART] is False
    assert cfg[OPT_SHOW_CONTEXT_MENU] is False
