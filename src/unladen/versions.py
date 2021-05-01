# -*- coding: utf-8 -*-

__all__ = ["Version", "parse"]

import re
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


def parse(
    ref: str,
    *,
    version_rules: Iterable[Rule] = VERSION_RULES,
    name_rules: Optional[Iterable[Rule]] = None,
    path_rules: Optional[Iterable[Rule]] = None,
    verbose: bool = False,
) -> Version:
    version = parse_ref(ref, rules=version_rules, verbose=verbose)
    if version is None:
        raise ValueError(f"Invalid parse of 'version' from '{ref}'")

    name = parse_ref(
        ref,
        rules=name_rules if name_rules else version_rules,
        verbose=verbose,
    )
    if name is None:
        raise ValueError(f"Invalid parse of 'name' from '{ref}'")

    path = parse_ref(
        ref,
        rules=path_rules if path_rules else version_rules,
        verbose=verbose,
    )
    if path is None:
        raise ValueError(f"Invalid parse of 'path' from '{ref}'")

    return Version(ref, normalize_version(version), name, path)


def normalize_version(version: str) -> str:
    try:
        return str(packaging.version.Version(version))
    except packaging.version.InvalidVersion:
        return version


def parse_ref(
    ref: str, *, rules: Iterable[Rule], verbose: bool = False
) -> Optional[str]:
    for pattern, fmt in rules:
        result = re.match(pattern, ref)
        if result is not None:
            return fmt.format(*result.groups())
    return None
