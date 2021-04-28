# -*- coding: utf-8 -*-

"""
Utilities for working with configuration files and click based on the
implementation from psf/black
"""

__all__ = ["find_project_root", "read_pyproject_toml"]

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import click
import toml


@lru_cache()
def find_project_root(srcs: Tuple[str, ...]) -> Path:
    """Return a directory containing .git, .hg, or pyproject.toml.

    That directory will be a common parent of all files and directories
    passed in `srcs`.

    If no directory in the tree contains a marker that would specify it's the
    project root, the root of the file system is returned.
    """
    if not srcs:
        return Path("/").resolve()

    path_srcs = [Path(Path.cwd(), src).resolve() for src in srcs]

    # A list of lists of parents for each 'src'. 'src' is included as a
    # "parent" of itself if it is a directory
    src_parents = [
        list(path.parents) + ([path] if path.is_dir() else [])
        for path in path_srcs
    ]

    common_base = max(
        set.intersection(*(set(parents) for parents in src_parents)),
        key=lambda path: path.parts,
    )

    for directory in (common_base, *common_base.parents):
        if (directory / ".git").exists():
            return directory

        if (directory / ".hg").is_dir():
            return directory

        if (directory / "pyproject.toml").is_file():
            return directory

    return directory


@lru_cache()
def find_user_pyproject_toml() -> Path:
    r"""Return the path to the top-level user configuration for black.

    This looks for ~\.unladen on Windows and ~/.config/unladen on Linux and
    other Unix systems.
    """
    if sys.platform == "win32":
        # Windows
        user_config_path = Path.home() / ".unladen"
    else:
        config_root = os.environ.get("XDG_CONFIG_HOME", "~/.config")
        user_config_path = Path(config_root).expanduser() / "unladen"
    return user_config_path.resolve()


def find_pyproject_toml(path_search_start: str) -> Optional[str]:
    """Find the absolute filepath to a pyproject.toml if it exists"""
    path_project_root = find_project_root(path_search_start)
    path_pyproject_toml = path_project_root / "pyproject.toml"
    if path_pyproject_toml.is_file():
        return str(path_pyproject_toml)

    try:
        path_user_pyproject_toml = find_user_pyproject_toml()
        return (
            str(path_user_pyproject_toml)
            if path_user_pyproject_toml.is_file()
            else None
        )
    except PermissionError:
        # We do not have access to the user-level config directory, ignore it
        return None


def parse_pyproject_toml(path_config: str) -> Dict[str, Any]:
    """Parse a pyproject toml file, pulling out relevant parts for unladen

    If parsing fails, will raise a toml.TomlDecodeError
    """
    pyproject_toml = toml.load(path_config)
    config = pyproject_toml.get("tool", {}).get("unladen", {})
    return {
        k.replace("--", "").replace("-", "_"): v for k, v in config.items()
    }


def read_pyproject_toml(
    ctx: click.Context, param: click.Parameter, value: Optional[str]
) -> Optional[str]:
    """Inject configuration from "pyproject.toml" into defaults in `ctx`

    Returns the path to a successfully found and read configuration file, None
    otherwise.
    """
    if not value:
        value = ctx.params.get("source", None)
        if value is None:
            return None
        value = find_pyproject_toml(value)
        if value is None:
            return None

    try:
        config = parse_pyproject_toml(value)
    except (toml.TomlDecodeError, OSError) as e:
        raise click.FileError(
            filename=value, hint=f"Error reading configuration file: {e}"
        )

    if not config:
        return None
    else:
        # Sanitize the values to be Click friendly. For more information
        # please see:
        # https://github.com/psf/black/issues/1458
        # https://github.com/pallets/click/issues/1567
        config = {
            k: str(v) if not isinstance(v, (list, dict)) else v
            for k, v in config.items()
        }

    target_version = config.get("target_version")
    if target_version is not None and not isinstance(target_version, list):
        raise click.BadOptionUsage(
            "target-version", "Config key target-version must be a list"
        )

    default_map: Dict[str, Any] = {}
    if ctx.default_map:
        default_map.update(ctx.default_map)
    default_map.update(config)

    ctx.default_map = default_map
    return value
