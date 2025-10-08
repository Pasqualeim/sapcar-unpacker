"""Utilities for working with the disp+work executable."""
from __future__ import annotations

import os
from typing import Iterable, List

from .powershell import get_powershell_exe, run_cmd

__all__ = [
    "find_dispwork",
    "extract_dispwork_main_section",
    "run_dispwork_version",
]


def find_dispwork(base_dir: str | os.PathLike[str]) -> str | None:
    """Locate disp+work recursively inside *base_dir* with heuristics."""

    base = os.path.abspath(os.fspath(base_dir))
    candidates: List[tuple[int, float, int, str]] = []
    for root, _dirs, files in os.walk(base):
        for name in files:
            lowered = name.lower()
            if lowered in {"disp+work", "disp+work.exe"}:
                full = os.path.join(root, name)
                try:
                    mtime = os.stat(full).st_mtime
                except OSError:
                    mtime = 0.0
                priority = 0
                lower_path = full.lower()
                if "ntamd64" in lower_path:
                    priority += 3
                if (
                    f"{os.sep}exe{os.sep}" in lower_path
                    or lower_path.endswith(f"{os.sep}exe")
                    or f"{os.sep}uc{os.sep}" in lower_path
                ):
                    priority += 2
                candidates.append((priority, mtime, -len(full), full))

    if not candidates:
        for fallback in ("disp+work.exe", "disp+work"):
            candidate = os.path.join(base, fallback)
            if os.path.isfile(candidate):
                return candidate
        return None

    candidates.sort(reverse=True)
    return candidates[0][3]


def extract_dispwork_main_section(lines: Iterable[str]) -> list[str]:
    """Extract the main section of ``disp+work -v`` output."""

    normalised = [(index, line or "", (line or "").strip().lower()) for index, line in enumerate(lines)]
    start_index = None
    end_index = None

    for index, raw, lowered in normalised:
        if lowered == "disp+work information":
            start_index = index
            if index > 0 and set(normalised[index - 1][1].strip()) <= {"-"}:
                start_index = index - 1
            break
    if start_index is None:
        return list(lines)

    for index, raw, lowered in normalised[start_index + 1 :]:
        if lowered == "disp+work patch information":
            end_index = index
            if index > 0 and set(normalised[index - 1][1].strip()) <= {"-"}:
                end_index = index - 1
            break

    if end_index is None:
        end_index = len(normalised)

    return [normalised[i][1] for i in range(start_index, end_index)]


def run_dispwork_version(base_dir: str, log_callback) -> int:
    """Execute ``disp+work -v`` (falling back to ``-V``) and stream output."""

    dispwork_path = find_dispwork(base_dir)
    if not dispwork_path:
        raise FileNotFoundError("disp+work not found")

    disp_dir = os.path.dirname(dispwork_path)
    disp_name = os.path.basename(dispwork_path)
    powershell = get_powershell_exe()

    buffer: list[str] = []

    def collect(line: str) -> None:
        buffer.append(line)

    rc = 1
    for flag in ("-v", "-V"):
        command = [
            powershell,
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            f'& ./"{disp_name}" {flag}',
        ]
        log_callback(f"Comando PowerShell: & ./\"{disp_name}\" {flag} (cwd={disp_dir})")
        rc = run_cmd(disp_dir, command, collect)
        if rc == 0:
            break
        log_callback(f"(info) disp+work ha restituito RC={rc} con {flag}. Provo alternativa...")

    for line in extract_dispwork_main_section(buffer):
        log_callback(line)

    return rc
