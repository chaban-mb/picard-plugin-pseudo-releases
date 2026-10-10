"""Pytest configuration and session fixtures for plugin tests."""

import os
import pytest

# Ensure offscreen Qt platform for all tests
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Session-scoped QApplication instance for Qt widget tests."""
    try:
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app
    except ImportError:
        return None
