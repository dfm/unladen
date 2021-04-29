# -*- coding: utf-8 -*-

__all__ = ["copy_source_to_target"]

from pathlib import Path
import shutil

import click


def copy_source_to_target(
    *,
    ctx: click.Context,
    source: Path,
    target: Path,
    ref: str,
    verbose: bool = False,
) -> None:
    target.mkdir(parents=True, exist_ok=True)
    fullpath = target / ref

    # Delete any existing directory or file at the target path
    if fullpath.exists():
        if verbose:
            click.secho(f"{fullpath} exists, overwriting")
        if fullpath.is_dir():
            shutil.rmtree(fullpath)
        else:
            fullpath.unlink()

    # Do the copy
    shutil.copytree(source, fullpath)
