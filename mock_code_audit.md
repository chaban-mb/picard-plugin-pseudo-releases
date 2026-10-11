# Mock & Headless Fallback Code Inventory and Audit

**Target Repository:** `picard-plugin-pseudo-releases`  
**Date:** 2026-10-11  
**Status:** Audit & Migration Roadmap  

---

## Executive Summary

The production codebase of `picard-plugin-pseudo-releases` currently contains defensive fallback shims and dummy Qt/Picard classes designed to allow unit testing and headless execution in environments where `PyQt6` or MusicBrainz Picard core libraries are not installed.

In actual production deployments (within MusicBrainz Picard 3.0+), Picard is always running with PyQt6 and its full API initialized; these mock classes are dead code in production and represent technical debt. This document provides an exhaustive inventory of all mock/shim code currently embedded in production modules, identifies which tests rely on them, and details the phased migration plan to relocate them into `tests/mocks/`.

---

## 1. Exhaustive Inventory of Production Mock Code

### 1.1 `options.py`

#### A. Dummy Qt Stubs (Lines 11–95)
*Triggered when `from PyQt6 import QtWidgets` raises `ImportError`.*

| Component | Lines | Purpose & Implemented Interface |
| :--- | :--- | :--- |
| `_DummySignal` | 12–21 | Minimal Qt signal mock providing `connect(callback)` and `emit(*args)`. |
| `_DummyWidget` | 23–85 | Universal mock widget standing in for all PyQt6 widget types. Implements dummy methods: `setStyleSheet`, `setLayout`, `addWidget`, `addLayout`, `addStretch`, `setContentsMargins`, `setSpacing`, `isChecked`, `setChecked`, `setEnabled`, `isEnabled`, `setWordWrap`, `setOpenExternalLinks`, `text`, `setText`, `title`, `addButton`, and dummy signals `toggled`, `clicked`, `linkActivated`. |
| `QtWidgets` namespace stub | 86–95 | Class mapping `QWidget`, `QVBoxLayout`, `QHBoxLayout`, `QLabel`, `QCheckBox`, `QPushButton`, `QGroupBox`, and `QFrame` to `_DummyWidget`. |

#### B. Fallback Picard Plugin API Stubs (Lines 103–113)
*Triggered when `from picard.plugin3.api import OptionsPage, PageOptionConfigs, t_` raises `ImportError`.*

| Component | Lines | Purpose & Implemented Interface |
| :--- | :--- | :--- |
| `OptionsPage` | 103–108 | Minimal base class subclassing `QtWidgets.QWidget` with `NAME = ""`, `TITLE = ""`, `PARENT = None`, and `api = None`. |
| `PageOptionConfigs` | 109 | Fallback type alias `dict[str, Any]`. |
| `t_` | 111–113 | Minimal translation function returning `text or key`. |

---

### 1.2 `compat.py`

#### A. Headless/Mock PyQt6 Stubs (Lines 8–143)
*Triggered when `from PyQt6 import QtCore, QtGui, QtWidgets` raises `ImportError`.*

| Component | Lines | Purpose & Implemented Interface |
| :--- | :--- | :--- |
| `QtCore` namespace stub | 8–23 | Defines stub `QObject`, `QEvent` (`MouseButtonRelease = 3`), and `Qt.MouseButton` (`NoButton = 0`, `LeftButton = 1`, `RightButton = 2`, `MiddleButton = 4`). |
| `_FallbackCursor` | 24–28 | Provides `pos() -> None`. |
| `QtGui` namespace stub | 29–41 | Maps `QCursor = _FallbackCursor` and defines stub `QActionGroup` (`setExclusive`, `addAction`). |
| `_FallbackFont` | 42–58 | Font state container providing `bold()`, `setBold()`, `underline()`, `setUnderline()`. |
| `_FallbackSignal` | 59–69 | Basic signal shim with `connect(callback)` and `emit(*args)`. |
| `_FallbackAction` | 70–106 | Mock `QAction` implementing `text`, `checked`, `checkable`, `enabled`, `triggered`, `font`, `setFont`, `data`, `setData`, `setToolTip`, `trigger`. |
| `_FallbackMenu` | 107–140 | Mock `QMenu` implementing `actions`, `parent`, `addAction`, `addSeparator`, `setToolTipsVisible`, `installEventFilter`, `actionAt`, `close`, `exec`, `deleteLater`. |
| `QtWidgets` namespace stub | 141–143 | Maps `QMenu = _FallbackMenu`. |

#### B. Picard Plugin API Fallbacks (Lines 159–205)
*Triggered when `from picard.plugin3.api import ...` raises `ImportError`.*

| Component | Lines | Purpose & Implemented Interface |
| :--- | :--- | :--- |
| `DebugOpt` | 159–160 | Minimal class defining `PLUGIN_DEVELOPMENT = "plugin-development"`. |
| `t_` | 162–165 | Fallback returning key or plural tuple. |
| `webbrowser2` | 167 | Fallback importing standard library `webbrowser as webbrowser2`. |
| `BaseAction` | 171–193 | Mock action base class implementing `tagger`, `_menu`, `_enabled`, `destroyed`, `setMenu`, `menu`, `setEnabled`, `isEnabled`. |
| `PluginApi` | 194–195 | Empty stub class. |
| `Album` | 197–198 | Empty stub class. |
| `Track` | 200–201 | Empty stub class. |
| `Metadata` | 203–204 | Empty stub class. |

---

### 1.3 `plugin.py`

#### Native Picard Utility Fallbacks (Lines 65–144)
*Triggered when `from picard.mbjson import ...`, `from picard.releasegroup import ...`, or `from picard.util import ...` raise `ImportError`.*

| Component | Lines | Purpose & Fallback Behavior |
| :--- | :--- | :--- |
| `countries_from_node` | 66–76 | Extracts ISO country codes from candidate `release-events` dictionaries. |
| `countries_shortlist` | 78–86 | Joins country codes with `+` and truncates using `…` for >6 countries. |
| `label_info_from_node` | 88–106 | Deduplicates labels and catalog numbers from `label-info` dictionaries. |
| `media_formats_from_node` | 108–130 | Deduplicates and counts media formats (e.g. `2×CD`). |
| `pgettext_attributes` | 132–133 | Identity function returning untranslated packaging name. |
| `_` | 135–136 | Identity function returning input string. |
| `VERSIONS_MAX_TRACKS` | 138 | Limit candidate edition track count segment display before `+…` truncation (10). |
| `VERSIONS_EXTRA_HEADINGS` | 139–143 | English literal mapping: `{'packaging': 'Packaging', 'barcode': 'Barcode', 'disambiguation': 'Disambiguation'}`. |

---

## 2. Test Dependency Mapping

| Test File | Depends On Mock Shims When | Tests Affected |
| :--- | :--- | :--- |
| `tests/test_options.py` | PyQt6 or Picard API uninstalled | `TestOptionsPage.test_options_page_metadata`, `test_tr_helper`, `test_load_and_save_options`, `test_ui_descriptions_and_groups` |
| `tests/test_plugin_lifecycle.py` | Picard core uninstalled | `test_plugin_enable_and_disable_lifecycle`, `test_action_registered`, `test_options_page_registered` |
| `tests/test_menu_gui.py` | PyQt6 uninstalled | `test_qmenu_middle_click_and_right_click_event_filter` |
| `tests/test_candidates.py` | Standalone CLI environment | `TestCandidateDiscovery`, `TestOriginalCandidateScoring` |
| `tests/test_real_fixtures.py` | Standalone CLI environment | Candidate formatting and tooltip rendering |

---

## 3. Migration Roadmap to `tests/mocks/`

To achieve clean production code in accordance with Picard Plugin v3 standards, all mock shims will be extracted into a dedicated test mock package:

### Phase 1: Establish Shared Test Mock Architecture
1. Create `tests/mocks/__init__.py`.
2. Create `tests/mocks/mock_qt.py`:
   - Move `_DummySignal`, `_DummyWidget`, `_FallbackAction`, `_FallbackMenu`, `_FallbackFont`, `_FallbackCursor` into this module.
3. Create `tests/mocks/mock_picard.py`:
   - Move `BaseAction`, `OptionsPage`, `PluginApi`, `Album`, `Track`, `Metadata`, `DebugOpt`, `t_` into this module.
4. Update `tests/conftest.py`:
   - Check if `PyQt6` and `picard` are importable.
   - If missing, mock them in `sys.modules` (`sys.modules['PyQt6'] = mock_qt`, `sys.modules['picard.plugin3.api'] = mock_picard`).

### Phase 2: Strip Production Files
1. **`options.py`**:
   - Replace lines 8–95 with direct `from PyQt6 import QtWidgets`.
   - Replace lines 96–113 with direct `from picard.plugin3.api import OptionsPage, PageOptionConfigs, t_`.
2. **`compat.py`**:
   - Strip all `_Fallback*` classes and dummy stubs.
   - Retain only necessary compatibility shims (e.g. `webbrowser2` alias) or eliminate the module in favor of direct public imports.
3. **`plugin.py`**:
   - Keep defensive fallbacks or transition to Picard dependency requirement (guaranteed by Picard plugin loader).

### Phase 3: Validation
1. Verify `pytest tests/` in standard test environment (with PyQt6 and sibling Picard repository).
2. Verify `pytest tests/` in headless CI container without display server.
3. Validate plugin loads cleanly inside Picard via `picard-cli plugins validate .`.
