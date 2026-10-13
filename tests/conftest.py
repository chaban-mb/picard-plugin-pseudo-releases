"""Pytest configuration and session fixtures for plugin tests."""

import os
from pathlib import Path
import sys
import types
import unittest.mock
import pytest

# Ensure offscreen Qt platform for all tests
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Add sibling Picard repository to sys.path if available so full Picard runtime imports work in tests
picard_repo = Path(__file__).resolve().parent.parent.parent / "picard"
if picard_repo.exists() and str(picard_repo) not in sys.path:
    sys.path.insert(0, str(picard_repo))

# Ensure C-extension dependencies not present in test python environment do not break Picard imports
for mod_name in [
    "mutagen",
    "mutagen.id3",
    "mutagen.flac",
    "mutagen.mp3",
    "mutagen.ogg",
    "pywintypes",
    "win32file",
    "win32pipe",
    "win32api",
    "win32con",
    "win32event",
    "win32process",
]:
    if mod_name not in sys.modules:
        try:
            __import__(mod_name)
        except ImportError:
            sys.modules[mod_name] = unittest.mock.MagicMock()

try:
    import picard
    picard.tagger_instance = lambda: None
    from picard.extension_points import item_actions
    item_actions.tagger_instance = lambda: None
    from picard.ui import options as options_module
    options_module.tagger_instance = lambda: None
    from picard import config as cfg_mod
    from types import SimpleNamespace
    fake_config = SimpleNamespace(
        setting={
            'caa_restrict_image_types': False,
            'caa_image_types': [],
            'caa_image_types_to_omit': [],
            'preferred_release_countries': [],
            'release_ars': False,
            'use_genres': False,
            'only_my_genres': False,
        },
        persist={},
        profiles={},
    )
    cfg_mod.config = fake_config
    cfg_mod.get_config = lambda: fake_config
except (ImportError, Exception):
    pass



# Setup fallback mocks if PyQt6 or picard are not installed or cannot be imported
try:
    import PyQt6
    from PyQt6 import QtCore, QtGui, QtWidgets
except ImportError:
    from tests.mocks import mock_qt

    qt_mod = types.ModuleType("PyQt6")
    qt_mod.QtCore = mock_qt.MockQtCore
    qt_mod.QtGui = mock_qt.MockQtGui
    qt_mod.QtWidgets = mock_qt.MockQtWidgets
    qt_mod.QtTest = mock_qt.MockQtTest
    sys.modules["PyQt6"] = qt_mod
    sys.modules["PyQt6.QtCore"] = mock_qt.MockQtCore
    sys.modules["PyQt6.QtGui"] = mock_qt.MockQtGui
    sys.modules["PyQt6.QtWidgets"] = mock_qt.MockQtWidgets
    sys.modules["PyQt6.QtTest"] = mock_qt.MockQtTest

try:
    import picard
    import picard.plugin3.api
    import picard.coverart.providers.caa
except ImportError:
    from tests.mocks import mock_picard

    if "picard" not in sys.modules:
        p_mod = types.ModuleType("picard")
        p_mod.config = unittest.mock.MagicMock()
        sys.modules["picard"] = p_mod
        sys.modules["picard.config"] = p_mod.config

    if "picard.plugin3.api" not in sys.modules:
        api_mod = types.ModuleType("picard.plugin3.api")
        api_mod.Album = mock_picard.Album
        api_mod.BaseAction = mock_picard.BaseAction
        api_mod.DebugOpt = mock_picard.DebugOpt
        api_mod.Metadata = mock_picard.Metadata
        api_mod.OptionsPage = mock_picard.OptionsPage
        api_mod.PageOptionConfigs = mock_picard.PageOptionConfigs
        api_mod.PluginApi = mock_picard.PluginApi
        api_mod.Track = mock_picard.Track
        api_mod.t_ = mock_picard.t_
        sys.modules["picard.plugin3.api"] = api_mod

    if "picard.coverart.providers.caa" not in sys.modules:
        caa_mod = types.ModuleType("picard.coverart.providers.caa")
        caa_mod.CoverArtProviderCaa = mock_picard.CoverArtProviderCaa
        sys.modules["picard.coverart.providers.caa"] = caa_mod

    if "picard.mbjson" not in sys.modules:
        mbjson_mod = types.ModuleType("picard.mbjson")
        mbjson_mod.countries_from_node = mock_picard.countries_from_node
        mbjson_mod.label_info_from_node = mock_picard.label_info_from_node
        mbjson_mod.media_formats_from_node = mock_picard.media_formats_from_node
        mbjson_mod._relations_to_metadata = unittest.mock.MagicMock()
        mbjson_mod.add_genres_from_node = mock_picard.add_genres_from_node
        sys.modules["picard.mbjson"] = mbjson_mod

    if "picard.releasegroup" not in sys.modules:
        rg_mod = types.ModuleType("picard.releasegroup")
        rg_mod.VERSIONS_EXTRA_HEADINGS = mock_picard.VERSIONS_EXTRA_HEADINGS
        rg_mod.VERSIONS_MAX_TRACKS = mock_picard.VERSIONS_MAX_TRACKS
        sys.modules["picard.releasegroup"] = rg_mod

    if "picard.util" not in sys.modules:
        util_mod = types.ModuleType("picard.util")
        util_mod.countries_shortlist = mock_picard.countries_shortlist
        util_mod.webbrowser2 = mock_picard.webbrowser2
        sys.modules["picard.util"] = util_mod

    if "picard.i18n" not in sys.modules:
        i18n_mod = types.ModuleType("picard.i18n")
        i18n_mod.gettext = mock_picard._
        i18n_mod.pgettext_attributes = mock_picard.pgettext_attributes
        sys.modules["picard.i18n"] = i18n_mod


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Session-scoped QApplication instance for Qt widget tests."""
    try:
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app
    except (ImportError, Exception):
        return None
