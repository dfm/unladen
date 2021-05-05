# -*- coding: utf-8 -*-

__all__ = ["Version", "Database", "parse"]

import json
import re
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Tuple,
    Union,
)

import packaging.version

Rule = Tuple[str, str]
VERSION_RULES: Tuple[Rule, ...] = (("refs/.+/(.+)", "{0}"),)
ALIAS_RULES: Tuple[Rule, ...] = (("refs/tags/v[0-9\\.]+", "stable"),)


class Version(NamedTuple):
    ref: str
    version: str
    name: str
    path: str
    active: bool = True

    @staticmethod
    def load(data: Dict[str, Any]) -> "Version":
        return Version(
            str(data["ref"]),
            str(data["version"]),
            str(data["name"]),
            str(data["path"]),
            bool(data["active"]),
        )

    def save(self) -> Dict[str, Union[str, List[str], bool]]:
        return {
            "ref": self.ref,
            "version": self.version,
            "name": self.name,
            "path": self.path,
            "active": self.active,
        }

    def __eq__(self, other: Any) -> bool:
        if not hasattr(other, "ref"):
            return NotImplemented
        return self.ref == other.ref

    def __lt__(self, other: Any) -> bool:
        if not hasattr(other, "version"):
            return NotImplemented
        return self.version < other.version


class Database:
    def __init__(
        self, versions: Dict[str, Version] = {}, aliases: Dict[str, str] = {}
    ):
        self.versions = versions
        self.aliases = aliases

    @staticmethod
    def load(path: Path) -> "Database":
        with open(path, "r") as f:
            data = json.load(f)
        return Database(
            versions={
                v.ref: v for v in map(Version.load, data.get("versions", []))
            },
            aliases=data.get("aliases", {}),
        )

    def save(self, path: Path) -> None:
        data = {
            "versions": [v.save() for v in self.versions.values()],
            "aliases": self.aliases,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def add_version(self, version: Version) -> None:
        self.versions[version.ref] = version

    def update_aliases(self, rules: Optional[Iterable[Rule]] = None) -> None:
        if rules is None:
            rules = ALIAS_RULES
        matches: Dict[str, str] = {}
        for v in sorted(self.versions.values(), reverse=True):
            name = _parse_ref(v.ref, rules=rules)
            if name and name not in matches:
                matches[name] = v.ref
        self.aliases = matches

    def __getitem__(self, ref: str) -> Version:
        return self.versions[ref]


def parse(
    ref: str,
    *,
    version_rules: Iterable[Rule] = VERSION_RULES,
    name_rules: Optional[Iterable[Rule]] = None,
    path_rules: Optional[Iterable[Rule]] = None,
    verbose: bool = False,
) -> Version:
    version = _parse_ref(ref, rules=version_rules, verbose=verbose)
    if version is None:
        raise ValueError(f"Invalid parse of 'version' from '{ref}'")

    name = _parse_ref(
        ref,
        rules=name_rules if name_rules else version_rules,
        verbose=verbose,
    )
    if name is None:
        raise ValueError(f"Invalid parse of 'name' from '{ref}'")

    path = _parse_ref(
        ref,
        rules=path_rules if path_rules else version_rules,
        verbose=verbose,
    )
    if path is None:
        raise ValueError(f"Invalid parse of 'path' from '{ref}'")

    return Version(ref, _normalize_version(version), name, path)


def _normalize_version(version: str) -> str:
    try:
        return str(packaging.version.Version(version))
    except packaging.version.InvalidVersion:
        return version


def _parse_ref(
    ref: str, *, rules: Iterable[Rule], verbose: bool = False
) -> Optional[str]:
    for pattern, fmt in rules:
        result = re.match(pattern, ref)
        if result is not None:
            return fmt.format(*result.groups())
    return None
