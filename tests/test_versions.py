# -*- coding: utf-8 -*-

import pytest

from unladen.versions import Version, parse


def test_version_load() -> None:
    data = dict(
        ref="refs/tags/v0.0.1",
        version="0.0.1",
        name="v0.0.1",
        path="stable/v0.0.1",
        active=True,
    )
    version = Version.load(data)
    assert version.version == "0.0.1"
    assert version.name == "v0.0.1"
    assert version.path == "stable/v0.0.1"


def test_version_roundtrip() -> None:
    data = dict(
        ref="refs/tags/v0.0.1",
        version="0.0.1",
        name="v0.0.1",
        path="stable/v0.0.1",
        active=False,
    )
    version = Version.load(data)
    for k, v in version.save().items():
        assert data[k] == v


def test_version_parse() -> None:
    version = parse("refs/heads/main")
    assert version.version == "main"
    assert version.name == "main"
    assert version.path == "main"
    assert version.active

    version = parse("refs/tags/v0.0.1")
    assert version.version == "0.0.1"
    assert version.name == "v0.0.1"
    assert version.path == "v0.0.1"


def test_version_compare() -> None:
    version1 = parse("refs/tags/v0.0.1")
    assert version1 == parse("refs/tags/v0.0.1")

    version2 = parse("refs/tags/v0.2.4")
    assert version1 < version2

    v1, v2 = sorted([version2, version1])
    assert v1 == version1
    assert v2 == version2


def test_version_parse_custom() -> None:
    rules = [("refs/heads/(.+)", "dev/{0}"), ("refs/tags/(.+)", "stable/{0}")]
    version = parse(ref="refs/heads/main", path_rules=rules)
    assert version.name == "main"
    assert version.path == "dev/main"

    version = parse(ref="refs/tags/v0.0.1", path_rules=rules)
    assert version.name == "v0.0.1"
    assert version.path == "stable/v0.0.1"


def test_invalid_version() -> None:
    with pytest.raises(ValueError):
        parse("un/recognized/ref")
