"""Pytest configuration and session fixtures for plugin tests."""

import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import types
import unittest.mock
import pytest

# Ensure offscreen Qt platform for all tests
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Add sibling Picard repository to sys.path if available so full Picard runtime imports work in tests
picard_repo = Path(__file__).resolve().parent.parent.parent / "picard"
if picard_repo.exists() and str(picard_repo) not in sys.path:
    sys.path.insert(0, str(picard_repo))

# Ensure optional native C-extension dependencies do not block importing Picard modules in test environments
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

import picard
from picard import config as cfg_mod
from picard.extension_points import item_actions
from picard.options import StandardizeArtistNames
from picard.ui import options as options_module

picard.tagger_instance = lambda: None
item_actions.tagger_instance = lambda: None
options_module.tagger_instance = lambda: None

fake_config = SimpleNamespace(
    setting={
        "caa_restrict_image_types": False,
        "caa_image_types": [],
        "caa_image_types_to_omit": [],
        "preferred_release_countries": [],
        "release_ars": False,
        "use_genres": False,
        "only_my_genres": False,
        "standardize_artist_names": StandardizeArtistNames.NONE,
        "translate_artist_names": False,
        "translate_artist_names_script_exception": False,
        "always_standardize_multivalue_artist": False,
        "standardize_instruments": True,
        "standardize_vocals": True,
        "translation_locales": ["en"],
    },
    persist={},
    profiles={},
)
cfg_mod.config = fake_config
cfg_mod.setting = fake_config.setting
cfg_mod.persist = fake_config.persist
cfg_mod.profiles = fake_config.profiles
cfg_mod.get_config = lambda: fake_config

repo_root = Path(__file__).resolve().parent.parent
package_name = "pseudo_releases"
if package_name not in sys.modules:
    spec = importlib.util.spec_from_file_location(
        package_name,
        str(repo_root / "__init__.py"),
        submodule_search_locations=[str(repo_root)],
    )
    if spec and spec.loader:
        pkg_mod = importlib.util.module_from_spec(spec)
        sys.modules[package_name] = pkg_mod
        sys.modules["__init__"] = pkg_mod
        spec.loader.exec_module(pkg_mod)

if "picard.plugins" not in sys.modules:
    sys.modules["picard.plugins"] = types.ModuleType("picard.plugins")
sys.modules["picard.plugins.pseudo_releases"] = sys.modules[package_name]
sys.modules["__init__"] = sys.modules[package_name]


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Session-scoped QApplication instance for Qt widget tests."""
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app
