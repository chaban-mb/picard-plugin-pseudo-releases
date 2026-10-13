"""In-process GUI tests using pytest-qt and QTest for context menu actions and browser lookup."""

import os
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

import __init__ as plugin_module


@pytest.fixture(autouse=True)
def ensure_offscreen():
    """Ensure offscreen platform to guarantee headless execution."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


from tests.mocks.mock_picard import MockAlbum, MockMetadata



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
    outer_menu = QtWidgets.QMenu(real_main_window)
    outer_menu.addAction("Parent context")
    qtbot.addWidget(outer_menu)

    mock_tagger = SimpleNamespace(
        window=real_main_window,
        config=None,
        get_file_lookup=MagicMock(return_value=mock_file_lookup),
    )
    real_main_window.selected_objects = [album]

    api = SimpleNamespace(
        tagger=mock_tagger,
        plugin_config={},
        logger=MagicMock(),
        tr=MagicMock(side_effect=lambda key, text=None, **kwargs: text or key),
    )
    plugin_module.PseudoReleasePlugin.api = api

    action = plugin_module.ChooseLinkedOriginalAction()
    action.tagger = mock_tagger
    menu = action.menu()
    assert isinstance(menu, QtWidgets.QMenu)
    qtbot.addWidget(menu)
    outer_menu.show()
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
    assert outer_menu.isVisible() is False
    # Verify main window is still open and was NOT closed
    assert real_main_window.isVisible() is True

    # Post MouseButtonRelease with RightButton over action2
    mock_file_lookup.reset_mock()
    outer_menu.show()
    menu.show()
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
    assert outer_menu.isVisible() is False
    assert real_main_window.isVisible() is True
