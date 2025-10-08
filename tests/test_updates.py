from sapcar_unpacker_core.updates import parse_version


def test_parse_version_handles_prefix_and_suffix():
    assert parse_version("v1.2.3") == (1, 2, 3)
    assert parse_version("1.2.3-beta") == (1, 2, 3)
    assert parse_version(" ") == ()
