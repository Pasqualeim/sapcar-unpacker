"""Persistence helpers for the GUI application."""
from __future__ import annotations

import os
from pathlib import Path


def settings_file() -> str:
    """Return the path to the JSON file storing GUI settings."""

    base = Path(os.environ.get("APPDATA", Path.home())) / "SapcarUnpacker"
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Ignore directory creation issues; the caller will fail when opening the file.
        pass
    return str(base / "settings.json")


__all__ = ["settings_file"]
