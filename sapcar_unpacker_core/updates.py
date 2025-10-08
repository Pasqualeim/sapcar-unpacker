"""Utilities to check for application updates via GitHub Releases."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple
import itertools
import json
import threading
import urllib.request
import webbrowser

from tkinter import messagebox

from . import GITHUB_REPO, GITHUB_USER, __version__


@dataclass(frozen=True)
class ReleaseInfo:
    """Information about the latest available release."""

    tag: str
    url: str


def parse_version(tag: str) -> Tuple[int, ...]:
    """Parse a semantic version tag into a tuple of integers."""
    tag = (tag or "").strip().lstrip("vV")
    parts: list[int] = []
    for chunk in tag.split("."):
        numeric = "".join(itertools.takewhile(str.isdigit, chunk))
        if not numeric:
            break
        parts.append(int(numeric))
    return tuple(parts)


def get_latest_release(timeout: float = 8.0) -> ReleaseInfo:
    """Return the tag and URL for the latest GitHub release."""

    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": f"{GITHUB_REPO}/{__version__}"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8", "replace"))

    tag = payload.get("tag_name") or payload.get("name") or ""
    html_url = payload.get("html_url") or f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases"
    return ReleaseInfo(tag=tag, url=html_url)


def _notify_update(parent, info: ReleaseInfo) -> None:
    if messagebox.askyesno(
        "Aggiornamento disponibile",
        f"È disponibile la versione {info.tag} (tu hai {__version__}).\nAprire la pagina Releases su GitHub?",
    ):
        webbrowser.open(info.url)


def check_updates_async(parent) -> None:
    """Check for updates in a background thread and notify the user."""

    def worker() -> None:
        try:
            info = get_latest_release()
            if info.tag and parse_version(info.tag) > parse_version(__version__):
                parent.after(0, lambda: _notify_update(parent, info))
        except Exception:
            # Ignore network errors silently to avoid disturbing the user.
            pass

    threading.Thread(target=worker, daemon=True).start()


__all__ = [
    "ReleaseInfo",
    "check_updates_async",
    "get_latest_release",
    "parse_version",
]
