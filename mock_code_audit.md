# Mock & Test Isolation Architecture Audit & Guide

**Target Repository:** `picard-plugin-pseudo-releases`  
**Date:** 2026-10-11  
**Status:** Completed & Consolidated  

---

## 1. Executive Summary & Core Principle

In earlier iterations of `picard-plugin-pseudo-releases`, the codebase suffered architectural degradation due to **tests dictating production code**. Developers wrote incomplete or ad-hoc test doubles (e.g. `SimpleNamespace()`, `None` values, incomplete dictionaries), and when tests failed with `AttributeError`, they added defensive duck-typing (`hasattr`, `getattr`, nested `try/except`, redundant `else:` branches) directly into production files.

This anti-pattern inverted the testing relationship: production code was contaminated with defensive checks for environments that never exist inside real MusicBrainz Picard.

### The Guiding Principle: Rule 14 (Pure Production Code & Mock Isolation)
> **Production code must reflect the pure Picard Plugin API v3 contract.**  
> Tests must adapt to the production architecture by providing accurate, canonical test doubles. Production code must NEVER be polluted with defensive shims, `hasattr` checks, or fallback duck-typing to accommodate incomplete test mocks.

---

## 2. Inventory of Purged Anti-Patterns

### 2.1 Defensive API Shims in Production Modules
The following defensive checks were identified and eradicated across the codebase:
- `api and hasattr(api, 'tr') else ...`: Redundant fallback. In Picard Plugin API v3, `api.tr` is a guaranteed method on `PluginApi`.
- `hasattr(api, 'add_album_task')`: Redundant check. Background task scheduling is a core contract of `PluginApi`.
- `hasattr(api, 'mb_api')`: Redundant check. Picard's MusicBrainz web service API is always provided.
- `hasattr(coverart, 'front_image_found')` and custom dummy fallbacks in `CoverArtProviderCaa.__init__`: Picard guarantees a real `CoverArt` instance with `.metadata`, `.release`, `.album`, and `.front_image_found`.
- `tagger` resolution duck-typing: Cleaned up to standard Picard resolution (`self.tagger or getattr(api, 'tagger', None) or tagger_instance()`).
- Complete elimination of `compat.py`: Embedded dummy Qt classes and fallback API stubs were removed from production and relocated to `tests/mocks/`.

### 2.2 Artificial Private-Method Probing Tests
Tests were previously constructed to call private methods with invalid parameters (e.g. passing `[None]` to `_prefetch_linked_original_details` and `_handle_supplement_pseudo`). These test cases were pruned:
- Picard extension points dispatch well-typed data (`album`, `metadata`, `release_node`).
- Testing artificial internal `None` states forced private functions to maintain defensive guards for impossible runtime conditions.
- Real error boundaries (such as task scheduling failures when Picard's task queue raises an exception) were preserved and verified.

---

## 3. Canonical Test Double Architecture (`tests/mocks/`)

All test doubles are strictly isolated within the `tests/` tree and cannot leak into production:

### 3.1 `tests/mocks/mock_picard.py`
Provides canonical mocks matching Picard 3.0+ internal behavior:
- `MockMetadata`: Mirrors `picard.metadata.Metadata` with internal `_data: dict[str, list[str]]`, full mapping methods (`keys()`, `values()`, `items()`, `__iter__()`, `__len__()`, `__delitem__()`), joined string `__getitem__`, `.get()`, `.getall()`, and `.copy()`.
- `MockTrack`: Mirrors `picard.track.Track` with `.metadata` containing `title` and `musicbrainz_recordingid`.
- `MockAlbum`: Mirrors `picard.album.Album` with `.id`, `.metadata`, `.tracks`, `.load()`, `._finalize_loading()`, `._pending_tasks`, `.add_task()`, `.complete_task()`, `.add_folksonomy_tag()`, `.add_genre()`, and `.iterfiles()`.
- `MockCoverArt`: Mirrors `picard.coverart.CoverArt` with `.album`, `.metadata`, `.release`, `.front_image_found`, and `.tagger`.
- `MockPluginConfig`: Dictionary subclass with `.register_option(name, default)` matching `picard.plugin3.config.PluginConfig`.
- `MockPluginApi`: Complete mock implementing the full `PluginApi` specification:
  - `add_album_task()`, `complete_album_task()`
  - `register_album_metadata_processor()`, `register_album_post_removal_processor()`
  - `register_album_action()`, `register_cover_art_provider()`, `register_options_page()`, `register_script_variable()`
  - `tr()`, `trn()`
  - `.logger`, `.mb_api`, `.tagger`, `.global_config`, `.plugin_config`, `.script_variables`

### 3.2 `tests/mocks/mock_qt.py`
Provides headless Qt stubs (`_DummyWidget`, `_DummySignal`, `_FallbackAction`, `_FallbackMenu`) used exclusively when running in headless environments where PyQt6 is not present.

---

## 4. Consolidated Test Suite Mapping

All test files now import standard test doubles from `tests.mocks.mock_picard` without any duplicate local classes:

| Test File | Previous State | Current Consolidated State |
| :--- | :--- | :--- |
| `tests/test_candidates.py` | Local `MockMetadata` & `MockFile` | Imports `MockMetadata`, `MockFile` from `tests.mocks.mock_picard` |
| `tests/test_caa.py` | Swallowed `(AttributeError, TypeError)` in queue test | Fully consolidated doubles; asserts `QueueState.WAIT` and task registration |
| `tests/test_supplement.py` | Local `MockMetadata` & local `DummyAlbum` | Imports `MockMetadata` and `MockAlbum` from `tests.mocks.mock_picard` |
| `tests/test_menu_gui.py` | Local `MockMetadata` & `MockAlbum` | Imports `MockAlbum`, `MockMetadata` from `tests.mocks.mock_picard` |
| `tests/test_real_fixtures.py` | Local `MockMetadata`, `MockAlbum`, `MockPluginConfig`, `MockPluginApi` | Imports canonical mocks from `tests.mocks.mock_picard` |
| `tests/test_plugin_lifecycle.py` | Local `MockMetadata`, `MockAlbum`, `MockPluginConfig`, `MockPluginApi` | Imports canonical mocks from `tests.mocks.mock_picard`; includes cancellation and error recovery tests |
| `tests/test_options.py` | Local `MockPluginApi` | Imports `MockPluginApi` from `tests.mocks.mock_picard` |
| `tests/test_options_gui.py` | Local `MockPluginApi` | Imports `MockPluginApi` from `tests.mocks.mock_picard` |

**Suite Result:** 53 tests passing in ~0.10s across both headless and desktop environments.

---

## 5. Rules for Future Development

1. **Never add `hasattr` checks to production code for Picard core services.** If an attribute or method is part of `picard.plugin3.api`, assume it is present. If a test raises `AttributeError`, fix the mock in `tests/mocks/mock_picard.py`.
2. **Never duplicate mocks across test files.** If a new capability or helper is needed in a test double, add it to `tests/mocks/mock_picard.py` so all tests benefit from a uniform implementation.
3. **Do not write artificial tests for invalid internal dispatches.** Test public extension points and realistic failure conditions (e.g. network/scheduler exceptions), not arbitrary internal states that cannot occur during Picard operation.
4. **Keep production dependencies standard.** Depend on `PyQt6` and `picard.plugin3.api` directly. Stubs and shims belong in `tests/`.
