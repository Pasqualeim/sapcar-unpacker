"""Helpers for dealing with Windows paths."""
from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=256)
def to_short_path(path: str) -> str:
    """Convert a Windows path to its 8.3 short representation when possible."""
    try:
        import ctypes  # type: ignore

        get_short_path = ctypes.windll.kernel32.GetShortPathNameW  # type: ignore[attr-defined]
        get_short_path.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
        buffer = ctypes.create_unicode_buffer(4096)
        result = get_short_path(path, buffer, len(buffer))
        if result and buffer.value:
            return buffer.value
        return path
    except Exception:
        return path


__all__ = ["to_short_path"]
