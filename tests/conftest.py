"""Pytest configuration and session fixtures for plugin tests."""

import os
from pathlib import Path
import sys
import pytest

# Add sibling Picard repository to sys.path if available so full Picard runtime imports work in tests
picard_repo = Path(__file__).resolve().parent.parent.parent / "picard"
if picard_repo.exists() and str(picard_repo) not in sys.path:
    sys.path.insert(0, str(picard_repo))

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
