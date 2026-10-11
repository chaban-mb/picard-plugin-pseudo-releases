"""UI action for manually selecting linked original editions."""

try:
    from .compat import (
        BaseAction,
        QtCore,
        QtGui,
        QtWidgets,
        t_,
    )
    from .constants import TAG_ORIGINAL_RELEASE_ID
    from .plugin import PseudoReleasePlugin
except (ImportError, ValueError):
    from compat import (
        BaseAction,
        QtCore,
        QtGui,
        QtWidgets,
        t_,
    )
    from constants import TAG_ORIGINAL_RELEASE_ID
    from plugin import PseudoReleasePlugin


class LinkedEditionsMenuFilter(QtCore.QObject):
    """Event filter on the linked editions menu to handle middle or right click."""

    def __init__(self, menu, tagger=None, parent=None):
        super().__init__(parent or menu)
        self._menu = menu
        self._tagger = tagger

    def eventFilter(self, obj, event):
        try:
            if (
                event.type() == QtCore.QEvent.Type.MouseButtonRelease
                and event.button() in {QtCore.Qt.MouseButton.MiddleButton, QtCore.Qt.MouseButton.RightButton}
            ):
                action = self._menu.actionAt(event.pos()) if hasattr(self._menu, 'actionAt') else None
                release_id = action.data() if (action and hasattr(action, 'data')) else None
                if release_id:
                    PseudoReleasePlugin.open_release_in_browser(release_id, self._tagger)
                    p = self._menu
                    while p and isinstance(p, QtWidgets.QMenu):
                        p.close()
                        p = p.parent()
                    return True
        except Exception:
            pass
        try:
            return super().eventFilter(obj, event) if hasattr(super(), 'eventFilter') else False
        except (TypeError, Exception):
            return False


class ChooseLinkedOriginalAction(BaseAction):
    """Choose which linked original release supplies metadata."""

    TITLE = t_("action.linked_original_editions", "Linked original editions")

    def __init__(self, parent=None):
        super().__init__(parent)
        if getattr(self, 'tagger', None) is None and getattr(PseudoReleasePlugin, 'api', None):
            self.tagger = getattr(PseudoReleasePlugin.api, 'tagger', None)

        window = getattr(self.tagger, 'window', None)
        albums = getattr(window, 'selected_objects', [])
        if len(albums) != 1:
            self.setEnabled(False)
            return

        album = albums[0]
        if album.metadata.get('releasestatus') != 'pseudo-release':
            self.setEnabled(False)
            return

        candidates = getattr(album, '_pseudo_original_candidates', [])
        if not candidates:
            self.setEnabled(False)
            return

        parent_widget = window if isinstance(window, QtWidgets.QWidget) else None
        menu = QtWidgets.QMenu(parent_widget)
        menu.setToolTipsVisible(True)
        self.destroyed.connect(lambda *_: menu.deleteLater())
        self.setMenu(menu)

        self._menu_filter = LinkedEditionsMenuFilter(menu, tagger=getattr(self, 'tagger', None), parent=menu)
        menu.installEventFilter(self._menu_filter)

        selection_group = QtGui.QActionGroup(menu)
        selection_group.setExclusive(True)

        heading_text = getattr(getattr(album, 'release_group', None), 'version_headings', None)
        if not heading_text:
            heading_text = "Tracks / Year / Country / Format / Label / Cat No"
        heading = menu.addAction(heading_text)
        heading_font = heading.font()
        heading_font.setBold(True)
        heading_font.setUnderline(False)
        heading.setFont(heading_font)
        heading.setEnabled(False)

        current_id = album.metadata.get(TAG_ORIGINAL_RELEASE_ID)
        if (
            not current_id
            and getattr(album, '_pseudo_original_selection_mode', 'automatic') == 'manual'
        ):
            current_id = getattr(album, '_pseudo_original_release_choice', None)
        detail_cache = getattr(album, '_pseudo_original_details', {})
        stub_cache = getattr(album, '_pseudo_candidate_stubs', {})
        seen_candidate_ids: set[str] = set()
        for candidate in candidates:
            release_id = candidate.get('id')
            if not release_id or release_id in seen_candidate_ids:
                continue
            seen_candidate_ids.add(release_id)
            details = detail_cache.get(release_id) or stub_cache.get(release_id, candidate)
            label = PseudoReleasePlugin._format_original_candidate(details).replace('&', '&&')
            action = menu.addAction(label)
            action.setData(release_id)
            tooltip = PseudoReleasePlugin._format_original_candidate_tooltip(details)
            if tooltip:
                action.setToolTip(tooltip)
            action.setCheckable(True)
            action.setChecked(release_id == current_id)
            selection_group.addAction(action)
            action.triggered.connect(
                lambda checked=False, selected_id=release_id: PseudoReleasePlugin.select_linked_original(
                    album,
                    selected_id,
                )
            )

    def callback(self, objs) -> None:
        pass
