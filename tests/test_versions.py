# -*- coding: utf-8 -*-

import tempfile
from pathlib import Path

import pytest

from unladen.versions import ALIAS_RULES, Database, Version, _parse_ref, parse


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


def test_version_invalid() -> None:
    with pytest.raises(ValueError):
        parse("un/recognized/ref")


def test_database_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "unladen.json"
        database = Database(
            versions={
                v.ref: v
                for v in map(parse, ["refs/heads/main", "refs/tags/v0.0.1"])
            },
            aliases={"stable": "refs/tags/v0.0.1"},
        )
        database.save(path)
        database2 = Database.load(path)

        for v1, v2 in zip(
            sorted(database.versions), sorted(database2.versions)
        ):
            assert v1 == v2

        assert len(database.aliases) == len(database2.aliases)
        for k, v in database2.aliases.items():
            assert database.aliases[k] == v


def test_update_aliases() -> None:
    database = Database(
        versions={
            v.ref: v
            for v in map(
                parse,
                ["refs/heads/main", "refs/tags/v0.0.1", "refs/tags/v0.1.2"],
            )
        },
        aliases={},
    )
    database.update_aliases()
    assert tuple(database.aliases.keys()) == ("stable",)
    assert database.aliases["stable"] == "refs/tags/v0.1.2"


def test_release_candidate() -> None:
    assert _parse_ref("refs/tags/v0.1.0", rules=ALIAS_RULES) == "stable"
    assert _parse_ref("refs/tags/v0.1.0rc1", rules=ALIAS_RULES) is None
