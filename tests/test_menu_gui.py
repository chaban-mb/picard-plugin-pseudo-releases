"""In-process GUI tests using pytest-qt and QTest for context menu actions and browser lookup."""

import os
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

import __init__ as plugin_module
from constants import (
    OPT_AUTO_SUPPLEMENT,
    OPT_SHOW_CONTEXT_MENU,
)


@pytest.fixture(autouse=True)
def ensure_offscreen():
    """Ensure offscreen platform to guarantee headless execution."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


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


class MockAlbum:
    def __init__(self, album_id, title="", status="Pseudo-Release"):
        self.id = album_id
        self.metadata = MockMetadata(
            {
                "album": title,
                "releasestatus": status.lower(),
            }
        )
        self.tracks = []
        self._pseudo_original_candidates = []


def test_qmenu_middle_click_and_right_click_event_filter(qtbot):
    """Test that middle-click and right-click on real QMenu actions trigger browser lookup."""
    album = MockAlbum("pseudo-id-1", "Test Title", status="Pseudo-Release")
    album._pseudo_original_candidates = [
        {
            "id": "rel-orig-1",
            "title": "Edition 1",
            "date": "2004",
            "country": "JP",
            "media": [{"format": "CD", "track-count": 10}],
            "label-info": [{"label": {"name": "TestLabel"}, "catalog-number": "CAT-001"}],
        },
        {
            "id": "rel-orig-2",
            "title": "Edition 2",
            "date": "2005",
            "country": "US",
            "media": [{"format": "Digital", "track-count": 10}],
            "label-info": [{"label": {"name": "TestLabel"}, "catalog-number": "CAT-002"}],
        },
    ]

    mock_file_lookup = MagicMock()
    real_main_window = QtWidgets.QMainWindow()
    qtbot.addWidget(real_main_window)
    real_main_window.show()

    mock_tagger = SimpleNamespace(
        window=real_main_window,
        config=None,
        get_file_lookup=MagicMock(return_value=mock_file_lookup),
    )
    real_main_window.selected_objects = [album]

    api = SimpleNamespace(
        tagger=mock_tagger,
        plugin_config={
            OPT_AUTO_SUPPLEMENT: True,
            OPT_SHOW_CONTEXT_MENU: True,
        },
        logger=MagicMock(),
    )
    plugin_module.PseudoReleasePlugin.api = api

    action = plugin_module.ChooseLinkedOriginalAction()
    action.tagger = mock_tagger
    menu = action.menu()
    assert isinstance(menu, QtWidgets.QMenu)
    qtbot.addWidget(menu)
    menu.show()

    # Menu actions: heading, candidate 1, candidate 2
    actions = menu.actions()
    assert len(actions) == 3
    action1 = actions[1]
    action2 = actions[2]
    assert action1.data() == "rel-orig-1"
    assert action2.data() == "rel-orig-2"

    # Post MouseButtonRelease with MiddleButton over action1
    pos1 = menu.actionGeometry(action1).center()
    event_middle = QtGui.QMouseEvent(
        QtCore.QEvent.Type.MouseButtonRelease,
        QtCore.QPointF(pos1),
        QtCore.QPointF(pos1),
        Qt.MouseButton.MiddleButton,
        Qt.MouseButton.MiddleButton,
        Qt.KeyboardModifier.NoModifier,
    )
    handled = QtWidgets.QApplication.sendEvent(menu, event_middle)
    assert handled is True
    mock_file_lookup.album_lookup.assert_called_once_with("rel-orig-1")
    # Verify main window is still open and was NOT closed
    assert real_main_window.isVisible() is True

    # Post MouseButtonRelease with RightButton over action2
    mock_file_lookup.reset_mock()
    pos2 = menu.actionGeometry(action2).center()
    event_right = QtGui.QMouseEvent(
        QtCore.QEvent.Type.MouseButtonRelease,
        QtCore.QPointF(pos2),
        QtCore.QPointF(pos2),
        Qt.MouseButton.RightButton,
        Qt.MouseButton.RightButton,
        Qt.KeyboardModifier.NoModifier,
    )
    handled_right = QtWidgets.QApplication.sendEvent(menu, event_right)
    assert handled_right is True
    mock_file_lookup.album_lookup.assert_called_once_with("rel-orig-2")
    assert real_main_window.isVisible() is True
