"""Helpers for invoking PowerShell commands."""
from __future__ import annotations

import shutil
import subprocess
from typing import Callable, Sequence

Command = Sequence[str]
LogCallback = Callable[[str], None]


def get_powershell_exe() -> str:
    """Return the best available PowerShell executable."""

    for candidate in ("powershell", "powershell.exe", "pwsh", "pwsh.exe"):
        path = shutil.which(candidate)
        if path:
            return path
    return "powershell"


def run_cmd(cwd: str | None, cmd: Command, log_callback: LogCallback) -> int:
    """Execute *cmd* and stream its combined output to *log_callback*."""

    try:
        process = subprocess.Popen(
            list(cmd),
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert process.stdout is not None  # For type checkers
        for line in process.stdout:
            log_callback(line.rstrip("\n"))
        return process.wait()
    except FileNotFoundError as exc:
        log_callback(f"[ERRORE] File non trovato: {exc}")
        return 127
    except Exception as exc:  # pragma: no cover - defensive fallback
        log_callback(f"[ERRORE] {exc}")
        return 1


__all__ = ["get_powershell_exe", "run_cmd"]
