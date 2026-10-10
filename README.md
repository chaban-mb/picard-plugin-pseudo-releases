# Pseudo-Releases

Supplements MusicBrainz pseudo-releases (such as Romaji, transliterated, or translated tracklists) with original release metadata and cover art from their linked original release.

---

## How It Works

[MusicBrainz pseudo-releases](https://musicbrainz.org/doc/Style/Specific_types_of_releases/Pseudo-Releases) contain alternate tracklists (such as transliterations or translations) linked to an original release via the [`transl-tracklisting`](https://musicbrainz.org/relationship/fc399d47-23a7-4c28-bfcf-0607a562b644) relationship. Because pseudo-releases are virtual representations rather than distinct releases, this plugin uses that relationship to bridge the gap: giving you translated or transliterated track titles while retaining full catalog metadata and artwork from the original release.

### Automatic Metadata Supplementation
When you load an album into Picard whose status is `pseudo-release`:
1. The plugin checks the `transl-tracklisting` release relationships for linked original editions.
2. It enriches your album with the original release's metadata tags (`date`, `releasecountry`, `barcode`, `label`, `catalognumber`, and media format specifications) while preserving your translated track titles and artist credits.
3. It sets the hidden Picard variable `%_original_musicbrainz_albumid%` to the original release's MBID, allowing your [tagger scripts and file naming scripts](https://picard-docs.musicbrainz.org/en/extending/scripting.html) to reference the original release ID.

### Cover Art
Pseudo-releases are not supposed to have cover art in MusicBrainz. The plugin provides a dedicated Cover Art Archive provider—**Cover Art Archive: Pseudo-Release (Original)**—that fetches artwork directly from the linked original release.

---

## Choosing Between Editions

When an album has multiple physical pressings (such as an initial limited edition, standard release, or releases for different countries), Picard automatically selects the best matching candidate based on track counts, Disc ID / TOC matches, barcode, and media format.

To manually choose a different pressing:

1. Right-click the loaded album in Picard's album pane.
2. Hover over **Plugins > Linked original editions**.
3. A menu of candidate editions is displayed, formatted with Picard's standard columns:
   ```text
   Tracks / Year / Country / Format / Label / Cat No
   ```
   Hovering over any edition displays packaging, barcode, and disambiguation details.
4. **Left-click** an edition to switch to it and reload the album with that edition's metadata.
5. **Middle-click** or **right-click** any edition to open that release directly on MusicBrainz in your web browser.

---

## Configuration

The plugin operates automatically upon being enabled. Configuration guidance and integration links can be viewed in Picard under **Options > Options... > Plugins > Pseudo-Releases**:

### Cover Art Integration
Cover art is retrieved via Picard's native cover art provider architecture. You can enable, disable, and prioritize **Cover Art Archive: Pseudo-Release (Original)** directly in Picard under **Options > Options... > Cover Art > Providers** (or by clicking **Configure Providers...** on the plugin options page).

## License

This project is licensed under the [MIT License](LICENSE).
