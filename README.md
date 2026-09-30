# MusicBrainz Picard Plugin: Pseudo-Releases

Seamlessly integrates MusicBrainz pseudo-releases into MusicBrainz Picard 3.0+.

## Key Features

1. **Supplement Pseudo-Releases**:
   * When loading a pseudo-release directly (e.g. Romaji or English translated tracklist), automatically retrieves missing physical and catalog metadata (`date`, `originaldate`, `releasecountry`, `barcode`, `label`, `catalognumber`, `media`) from the linked original release.
   * Supplements cover artwork via the Cover Art Archive (CAA) using the original release ID.

2. **Overlay Pseudo-Releases onto Originals**:
   * When loading an official release (e.g. Japanese Kanji) via CD lookup, AcoustID, or search, automatically overlays translated or transliterated release and track titles.
   * **Full Artist Credit & Join Phrase Translation**: Preserves and translates join phrases (e.g. ` と ` / ` ＆ ` transformed to ` and ` / ` feat. `), solving Picard's alias-based join phrase limitation.
   * Retains physical manufacturing data (original barcodes, dates, catalog numbers, and CAA artwork).

3. **Intelligent Disambiguation**:
   * Evaluates Disc ID / TOC matches, track counts, medium layouts, and file tag fingerprints to pick the best candidate among multi-format editions (e.g. CD vs. Vinyl vs. Digital).

## Installation

### Manual Installation
Copy the `picard-plugin-pseudo-releases` folder into your Picard v3 plugins directory:
* **Windows**: `%APPDATA%\MusicBrainz\Picard\plugins3\`
* **Linux**: `~/.config/MusicBrainz/Picard/plugins3/`
* **macOS**: `~/Library/Preferences/MusicBrainz/Picard/plugins3/`

### CLI Installation
```bash
picard-cli plugins install /path/to/picard-plugin-pseudo-releases
```

## Requirements
* MusicBrainz Picard 3.0 or higher
* Python 3.10 or higher

## License
GNU General Public License v2.0 or later (GPL-2.0-or-later).
