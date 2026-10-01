# MusicBrainz Picard Plugin: Pseudo-Releases

Seamlessly integrates MusicBrainz pseudo-releases into MusicBrainz Picard 3.0+.

## Key Features

1. **Supplement Pseudo-Releases**:
   * When loading a pseudo-release directly (e.g. Romaji or English translated tracklist), automatically retrieves missing physical and catalog metadata (`date`, `originaldate`, `releasecountry`, `barcode`, `label`, `catalognumber`, `media`) from the linked original release.
   * Supplements cover artwork via the Cover Art Archive (CAA) using the original release ID.

2. **Intelligent Disambiguation**:
   * Ranks linked original editions using available Disc ID / TOC, track-count, barcode, format, catalog-number, status, and cover-art data.
   * Right-click a pseudo-release, hover **Plugins > Linked original editions**, and choose a linked source. Picard preloads edition details while the pseudo-release is processed, so opening the submenu makes no web requests. Choose **Automatic best match** to return to automatic selection.

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
MIT License.
