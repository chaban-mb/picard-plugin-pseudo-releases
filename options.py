# MusicBrainz Picard Plugin: Pseudo-Releases
#
# Copyright (C) 2026 Picard Community
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

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
    class _DummySignal:
        def __init__(self):
            self._callbacks = []

        def connect(self, callback):
            self._callbacks.append(callback)

        def emit(self, *args):
            for callback in self._callbacks:
                callback(*args)

    class _DummyWidget:
        def __init__(self, *args, **kwargs):
            self._checked = False
            self._enabled = True
            self._tool_tip = ""
            self.toggled = _DummySignal()

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
            checked = bool(val)
            if checked != self._checked:
                self._checked = checked
                self.toggled.emit(checked)

        def setEnabled(self, enabled):
            self._enabled = bool(enabled)

        def isEnabled(self):
            return self._enabled

        def setToolTip(self, text):
            self._tool_tip = text

        def toolTip(self):
            return self._tool_tip

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
        get_config_value,
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
        get_config_value,
    )


class PseudoReleaseOptionsPage(OptionsPage):
    """Picard Options page for configuring Pseudo-Release features."""

    NAME = "pseudo_releases"
    TITLE = "Pseudo-Releases"

    def _tr(self, key: str, text: str) -> str:
        """Translate text if Picard API tr is available, otherwise return default text."""
        api = getattr(self, 'api', None)
        if api and hasattr(api, 'tr'):
            try:
                res = api.tr(key, text)
                if res:
                    return res
            except Exception:
                pass
        return text

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # 1. Main Features
        group_features = QtWidgets.QGroupBox(
            self._tr("ui.group_features", "Pseudo-Release Features"),
            self,
        )
        features_layout = QtWidgets.QVBoxLayout(group_features)

        self.cb_enabled = QtWidgets.QCheckBox(
            self._tr("ui.enable_plugin", "Enable Pseudo-Release support"),
            group_features,
        )
        self.cb_enabled.setToolTip(self._tr(
            "ui.enable_plugin_tooltip",
            "Master switch for all pseudo-release features, including supplementation and translation overlays.",
        ))
        features_layout.addWidget(self.cb_enabled)

        self.cb_auto_supplement = QtWidgets.QCheckBox(
            self._tr(
                "ui.auto_supplement",
                "Supplement pseudo-releases with original catalog metadata & cover art",
            ),
            group_features,
        )
        self.cb_auto_supplement.setToolTip(self._tr(
            "ui.auto_supplement_tooltip",
            "When loading a pseudo-release, fill in missing catalog metadata and cover art from its linked original release.",
        ))
        features_layout.addWidget(self.cb_auto_supplement)

        self.cb_auto_overlay = QtWidgets.QCheckBox(
            self._tr(
                "ui.auto_overlay",
                "Automatically translate original releases using pseudo-releases",
            ),
            group_features,
        )
        self.cb_auto_overlay.setToolTip(self._tr(
            "ui.auto_overlay_tooltip",
            "When loading an original release, apply track titles and artist credits from a related pseudo-release.",
        ))
        features_layout.addWidget(self.cb_auto_overlay)

        self.cb_enabled.toggled.connect(self._update_control_states)
        self.cb_auto_overlay.toggled.connect(self._update_control_states)

        layout.addWidget(group_features)

        # 2. Preferred Translation / Transliteration Script
        group_script = QtWidgets.QGroupBox(
            self._tr("ui.group_script", "Preferred Translation Script / Language"),
            self,
        )
        script_layout = QtWidgets.QVBoxLayout(group_script)

        self.btn_group_script = QtWidgets.QButtonGroup(self)

        self.rb_latn = QtWidgets.QRadioButton(
            self._tr("ui.script_latn", "Latin script / Romaji transliterations (e.g. Hepburn Romaji)"),
            group_script,
        )
        self.rb_latn.setToolTip(self._tr(
            "ui.script_latn_tooltip",
            "Prefer Latin-script transliterations, such as Romaji, when choosing a pseudo-release.",
        ))
        self.btn_group_script.addButton(self.rb_latn)
        script_layout.addWidget(self.rb_latn)

        self.rb_eng = QtWidgets.QRadioButton(
            self._tr("ui.script_eng", "English translations"),
            group_script,
        )
        self.rb_eng.setToolTip(self._tr(
            "ui.script_eng_tooltip",
            "Prefer English translations when choosing a pseudo-release.",
        ))
        self.btn_group_script.addButton(self.rb_eng)
        script_layout.addWidget(self.rb_eng)

        self.rb_locales = QtWidgets.QRadioButton(
            self._tr("ui.script_locales", "Match Picard user interface language"),
            group_script,
        )
        self.rb_locales.setToolTip(self._tr(
            "ui.script_locales_tooltip",
            "Prefer pseudo-releases in languages matching Picard's user interface language.",
        ))
        self.btn_group_script.addButton(self.rb_locales)
        script_layout.addWidget(self.rb_locales)

        layout.addWidget(group_script)

        # 3. Behavior Rules
        group_behavior = QtWidgets.QGroupBox(
            self._tr("ui.group_behavior", "Translation Rules"),
            self,
        )
        behavior_layout = QtWidgets.QVBoxLayout(group_behavior)

        self.cb_skip_latin = QtWidgets.QCheckBox(
            self._tr(
                "ui.skip_latin",
                "Skip translation if original release is already in Latin script",
            ),
            group_behavior,
        )
        self.cb_skip_latin.setToolTip(self._tr(
            "ui.skip_latin_tooltip",
            "Do not overlay translations when the original release is already identified as Latin script.",
        ))
        behavior_layout.addWidget(self.cb_skip_latin)

        layout.addWidget(group_behavior)
        layout.addStretch()
        self._update_control_states()

    def _update_control_states(self, *_):
        """Disable settings that cannot apply while their parent feature is off."""
        enabled = self.cb_enabled.isChecked()
        overlay_enabled = enabled and self.cb_auto_overlay.isChecked()

        self.cb_auto_supplement.setEnabled(enabled)
        self.cb_auto_overlay.setEnabled(enabled)
        for widget in (self.rb_latn, self.rb_eng, self.rb_locales, self.cb_skip_latin):
            widget.setEnabled(overlay_enabled)

    def load(self):
        """Load settings from plugin configuration into UI widgets."""
        if not hasattr(self, 'api') or not self.api:
            return

        cfg = self.api.plugin_config
        self.cb_enabled.setChecked(get_config_value(cfg, OPT_ENABLED, True))
        self.cb_auto_supplement.setChecked(get_config_value(cfg, OPT_AUTO_SUPPLEMENT, True))
        self.cb_auto_overlay.setChecked(get_config_value(cfg, OPT_AUTO_OVERLAY, True))

        mode = get_config_value(cfg, OPT_TARGET_SCRIPT_MODE, SCRIPT_MODE_LATN)
        if mode == SCRIPT_MODE_ENG:
            self.rb_eng.setChecked(True)
        elif mode == SCRIPT_MODE_LOCALES:
            self.rb_locales.setChecked(True)
        else:
            self.rb_latn.setChecked(True)

        self.cb_skip_latin.setChecked(get_config_value(cfg, OPT_SKIP_LATIN_ORIGINALS, True))
        self._update_control_states()

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
