# MusicBrainz Picard Plugin: Pseudo-Releases
#
# Copyright (C) 2026 Picard Community
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, see <https://www.gnu.org/licenses/>.

"""Options page for user configuration of pseudo-release features."""

from typing import Any

try:
    from PyQt6 import QtWidgets
    from picard.plugin3.api import (
        OptionsPage,
        t_,
    )
except ImportError:
    # Stubs for headless testing environments without PyQt6
    class _DummyWidget:
        def __init__(self, *args, **kwargs):
            self._checked = False

        def setStyleSheet(self, *args):
            pass

        def setLayout(self, *args):
            pass

        def addWidget(self, *args):
            pass

        def addStretch(self, *args):
            pass

        def isChecked(self):
            return self._checked

        def setChecked(self, val):
            self._checked = bool(val)

        def addButton(self, *args):
            pass

    class QtWidgets:  # type: ignore[no-redef]
        QWidget = _DummyWidget
        QGroupBox = _DummyWidget
        QVBoxLayout = _DummyWidget
        QCheckBox = _DummyWidget
        QRadioButton = _DummyWidget
        QButtonGroup = _DummyWidget

    class OptionsPage(QtWidgets.QWidget):  # type: ignore[no-redef]
        NAME = ""
        TITLE = ""
        api: Any = None

    def t_(key: str, text: str | None = None, plural: str | None = None) -> str:  # type: ignore[no-redef]
        return text or key

try:
    from .constants import (
        OPT_AUTO_OVERLAY,
        OPT_AUTO_SUPPLEMENT,
        OPT_ENABLED,
        OPT_SKIP_LATIN_ORIGINALS,
        OPT_TARGET_SCRIPT_MODE,
        SCRIPT_MODE_ENG,
        SCRIPT_MODE_LATN,
        SCRIPT_MODE_LOCALES,
    )
except (ImportError, ValueError):
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


class PseudoReleaseOptionsPage(OptionsPage):
    """Picard Options page for configuring Pseudo-Release features."""

    NAME = "pseudo_releases"
    TITLE = t_("ui.options_title", "Pseudo-Releases")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # 1. Main Features
        group_features = QtWidgets.QGroupBox(
            t_("ui.group_features", "Pseudo-Release Features"),
            self,
        )
        features_layout = QtWidgets.QVBoxLayout(group_features)

        self.cb_enabled = QtWidgets.QCheckBox(
            t_("ui.enable_plugin", "Enable Pseudo-Release support"),
            group_features,
        )
        features_layout.addWidget(self.cb_enabled)

        self.cb_auto_supplement = QtWidgets.QCheckBox(
            t_(
                "ui.auto_supplement",
                "Supplement pseudo-releases with original catalog metadata & cover art (Goal 1)",
            ),
            group_features,
        )
        features_layout.addWidget(self.cb_auto_supplement)

        self.cb_auto_overlay = QtWidgets.QCheckBox(
            t_(
                "ui.auto_overlay",
                "Automatically translate original releases using pseudo-releases (Bonus Goal)",
            ),
            group_features,
        )
        features_layout.addWidget(self.cb_auto_overlay)

        layout.addWidget(group_features)

        # 2. Preferred Translation / Transliteration Script
        group_script = QtWidgets.QGroupBox(
            t_("ui.group_script", "Preferred Translation Script / Language"),
            self,
        )
        script_layout = QtWidgets.QVBoxLayout(group_script)

        self.btn_group_script = QtWidgets.QButtonGroup(self)

        self.rb_latn = QtWidgets.QRadioButton(
            t_("ui.script_latn", "Latin script / Romaji transliterations (e.g. Hepburn Romaji)"),
            group_script,
        )
        self.btn_group_script.addButton(self.rb_latn)
        script_layout.addWidget(self.rb_latn)

        self.rb_eng = QtWidgets.QRadioButton(
            t_("ui.script_eng", "English translations"),
            group_script,
        )
        self.btn_group_script.addButton(self.rb_eng)
        script_layout.addWidget(self.rb_eng)

        self.rb_locales = QtWidgets.QRadioButton(
            t_("ui.script_locales", "Match Picard user interface language"),
            group_script,
        )
        self.btn_group_script.addButton(self.rb_locales)
        script_layout.addWidget(self.rb_locales)

        layout.addWidget(group_script)

        # 3. Behavior Rules
        group_behavior = QtWidgets.QGroupBox(
            t_("ui.group_behavior", "Translation Rules"),
            self,
        )
        behavior_layout = QtWidgets.QVBoxLayout(group_behavior)

        self.cb_skip_latin = QtWidgets.QCheckBox(
            t_(
                "ui.skip_latin",
                "Skip translation if original release is already in Latin script",
            ),
            group_behavior,
        )
        behavior_layout.addWidget(self.cb_skip_latin)

        layout.addWidget(group_behavior)
        layout.addStretch()

    def load(self):
        """Load settings from plugin configuration into UI widgets."""
        if not hasattr(self, 'api') or not self.api:
            return

        cfg = self.api.plugin_config
        self.cb_enabled.setChecked(cfg.get(OPT_ENABLED, True))
        self.cb_auto_supplement.setChecked(cfg.get(OPT_AUTO_SUPPLEMENT, True))
        self.cb_auto_overlay.setChecked(cfg.get(OPT_AUTO_OVERLAY, True))

        mode = cfg.get(OPT_TARGET_SCRIPT_MODE, SCRIPT_MODE_LATN)
        if mode == SCRIPT_MODE_ENG:
            self.rb_eng.setChecked(True)
        elif mode == SCRIPT_MODE_LOCALES:
            self.rb_locales.setChecked(True)
        else:
            self.rb_latn.setChecked(True)

        self.cb_skip_latin.setChecked(cfg.get(OPT_SKIP_LATIN_ORIGINALS, True))

    def save(self):
        """Save settings from UI widgets into plugin configuration."""
        if not hasattr(self, 'api') or not self.api:
            return

        cfg = self.api.plugin_config
        cfg[OPT_ENABLED] = self.cb_enabled.isChecked()
        cfg[OPT_AUTO_SUPPLEMENT] = self.cb_auto_supplement.isChecked()
        cfg[OPT_AUTO_OVERLAY] = self.cb_auto_overlay.isChecked()

        if self.rb_eng.isChecked():
            cfg[OPT_TARGET_SCRIPT_MODE] = SCRIPT_MODE_ENG
        elif self.rb_locales.isChecked():
            cfg[OPT_TARGET_SCRIPT_MODE] = SCRIPT_MODE_LOCALES
        else:
            cfg[OPT_TARGET_SCRIPT_MODE] = SCRIPT_MODE_LATN

        cfg[OPT_SKIP_LATIN_ORIGINALS] = self.cb_skip_latin.isChecked()
