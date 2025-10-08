import os
from pathlib import Path

from sapcar_unpacker_core.dispwork import extract_dispwork_main_section, find_dispwork


def test_find_dispwork_prefers_ntamd64(tmp_path):
    base = tmp_path
    (base / "dir" / "exe").mkdir(parents=True)
    (base / "other").mkdir()

    # Old executable
    old = base / "other" / "disp+work.exe"
    old.write_text("", encoding="utf-8")
    os.utime(old, (1, 1))

    # Preferred executable due to ntamd64 hint and newer timestamp
    preferred_dir = base / "dir" / "exe" / "ntamd64"
    preferred_dir.mkdir(parents=True, exist_ok=True)
    preferred = preferred_dir / "disp+work"
    preferred.write_text("", encoding="utf-8")

    selected = find_dispwork(str(base))
    assert selected is not None
    assert Path(selected) == preferred


def test_extract_dispwork_main_section_filters_patch_info():
    lines = [
        "Some header",
        "--------------------------",
        "disp+work information",
        "Main line",
        "--------------------------",
        "disp+work patch information",
        "Patch line",
    ]

    result = extract_dispwork_main_section(lines)
    assert result == [
        "--------------------------",
        "disp+work information",
        "Main line",
    ]
