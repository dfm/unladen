# -*- coding: utf-8 -*-

__all__ = ["copy_source_to_target"]

import shutil
from pathlib import Path
from typing import Iterable, Optional

import click

from .versions import Database, Rule, Version


def copy_source_to_target(
    *,
    source: Path,
    target: Path,
    version: Version,
    alias_rules: Optional[Iterable[Rule]] = None,
    verbose: bool = False,
) -> None:
    target.mkdir(parents=True, exist_ok=True)

    # Load the database if it exists
    database_path = target / "unladen.json"
    if database_path.is_file():
        database = Database.load(database_path)
    else:
        database = Database()

    # Add this version to the database
    database.add_version(version)
    fullpath = target / version.path

    # Delete any existing directory or file at the target path
    rm_file_or_dir(fullpath, verbose=verbose)

    # Copy the files
    shutil.copytree(source, fullpath)

    # Remove existing aliases
    for name in database.aliases.keys():
        rm_file_or_dir(target / name, verbose=verbose)

    # Update alias links
    database.update_aliases(rules=alias_rules)
    for name, ref in database.aliases.items():
        try:
            ref_version = database[ref]
        except KeyError:
            click.secho(
                f"Alias {name} for ref {ref} has no matching version", err=True
            )
            continue

        src = target / ref_version.path
        dst = target / name
        rm_file_or_dir(dst, verbose=verbose)
        if verbose:
            click.secho(f"Copying {src} -> {dst}")
        shutil.copytree(src, dst)

    database.save(database_path)


def rm_file_or_dir(path: Path, verbose: bool = False) -> None:
    if path.exists():
        if verbose:
            click.secho(f"{path} exists, removing")
        if path.is_file() or path.is_symlink():
            path.unlink()
        else:
            shutil.rmtree(path)
