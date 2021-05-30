# -*- coding: utf-8 -*-

__all__ = ["copy_source_to_target"]

import shutil
from glob import glob
from pathlib import Path
from typing import Iterable, Optional

from . import html
from .versions import Database, Rule, Version


def copy_source_to_target(
    *,
    source: Path,
    target: Path,
    version: Version,
    base_url: Optional[str] = None,
    alias_rules: Optional[Iterable[Rule]] = None,
    include_version_menu: bool = True,
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
            print(f"Alias {name} for ref {ref} has no matching version")
            continue

        src = target / ref_version.path
        dst = target / name
        rm_file_or_dir(dst, verbose=verbose)
        if verbose:
            print(f"Copying {src} -> {dst}")
        shutil.copytree(src, dst)

    database.save(database_path)

    # Inject the version info into the HTML
    if include_version_menu:
        version_style = html.load_style("versions")
        version_menu = html.render_template(
            "versions",
            database=database,
            current_version=version,
            base_url=base_url,
        )

        for filename in glob(f"{fullpath}/**/*.html", recursive=True):
            print(filename)
            with open(filename, "r") as f:
                txt = f.read()
            txt = html.inject_into_html(
                txt, version_style=version_style, version_menu=version_menu
            )
            with open(filename, "w") as f:
                f.write(txt)


def rm_file_or_dir(path: Path, verbose: bool = False) -> None:
    if path.exists():
        if verbose:
            print(f"{path} exists, removing")
        if path.is_file() or path.is_symlink():
            path.unlink()
        else:
            shutil.rmtree(path)
