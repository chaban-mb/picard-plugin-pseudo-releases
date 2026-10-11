"""Pseudo-Releases Picard plugin for catalog and cover-art supplementation."""

try:
    from .action import (
        ChooseLinkedOriginalAction,
        LinkedEditionsMenuFilter,
    )
    from .caa_provider import PseudoReleaseCoverArtProvider
    from .compat import (
        QtCore,
        QtGui,
        QtWidgets,
        PluginApi,
        config,
        t_,
    )
    from .options import PseudoReleaseOptionsPage
    from .plugin import PseudoReleasePlugin
except (ImportError, ValueError):
    from action import (
        ChooseLinkedOriginalAction,
        LinkedEditionsMenuFilter,
    )
    from caa_provider import PseudoReleaseCoverArtProvider
    from compat import (
        QtCore,
        QtGui,
        QtWidgets,
        PluginApi,
        config,
        t_,
    )
    from options import PseudoReleaseOptionsPage
    from plugin import PseudoReleasePlugin


class ManifestTranslations:
    """Translation strings for the plugin manifest."""

    NAME = t_("manifest.name", "Pseudo-Releases")
    DESC = t_(
        "manifest.description",
        "Supplements pseudo-releases with original catalog metadata and cover art.",
    )


def enable(api: PluginApi) -> None:
    """Called when the plugin is enabled in Picard."""
    PseudoReleasePlugin.api = api

    # Register album metadata processor
    api.register_album_metadata_processor(PseudoReleasePlugin.process_album_metadata, priority=50)

    # Register a manual chooser for linked original editions
    if hasattr(api, 'register_album_action'):
        api.register_album_action(ChooseLinkedOriginalAction)

    # Register post-removal processor for cleanup
    if hasattr(api, 'register_album_post_removal_processor'):
        api.register_album_post_removal_processor(PseudoReleasePlugin.remove_album)

    # Register Cover Art Archive provider
    api.register_cover_art_provider(PseudoReleaseCoverArtProvider)

    # Register Options page
    api.register_options_page(PseudoReleaseOptionsPage)

    # Register custom script variables
    if hasattr(api, 'register_script_variable'):
        title = (
            api.tr("variable.original_albumid.title", "Original MusicBrainz Album ID")
            if hasattr(api, 'tr')
            else "Original MusicBrainz Album ID"
        )
        doc = (
            api.tr(
                "variable.original_albumid.doc",
                "MusicBrainz Release ID of the linked original release for pseudo-releases",
            )
            if hasattr(api, 'tr')
            else "MusicBrainz Release ID of the linked original release for pseudo-releases"
        )
        api.register_script_variable(
            "_original_musicbrainz_albumid",
            documentation=doc,
            title=title,
        )


def disable(api: PluginApi | None = None) -> None:
    """Called when the plugin is disabled in Picard."""
    PseudoReleasePlugin.in_flight_albums.clear()
    PseudoReleasePlugin.api = None


__all__ = [
    "ChooseLinkedOriginalAction",
    "LinkedEditionsMenuFilter",
    "ManifestTranslations",
    "PseudoReleaseCoverArtProvider",
    "PseudoReleaseOptionsPage",
    "PseudoReleasePlugin",
    "QtCore",
    "QtGui",
    "QtWidgets",
    "config",
    "disable",
    "enable",
]
