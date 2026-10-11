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
    )
    from options import PseudoReleaseOptionsPage
    from plugin import PseudoReleasePlugin


class ManifestTranslations:
    """Translation strings for the plugin manifest."""

    NAME = "Pseudo-Releases"
    DESC = (
        "Supplements pseudo-releases with original catalog metadata and cover art."
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
