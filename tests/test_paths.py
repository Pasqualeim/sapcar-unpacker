from sapcar_unpacker_core.paths import to_short_path


def test_to_short_path_returns_original_on_non_windows(tmp_path):
    path = tmp_path / "Some Folder"
    path.mkdir()
    resolved = to_short_path(str(path))
    assert isinstance(resolved, str)
    # On non-Windows platforms the function should fall back to the original path.
    assert resolved.lower().replace("\\", "/") == str(path).lower().replace("\\", "/")
