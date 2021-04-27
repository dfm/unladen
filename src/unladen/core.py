# -*- coding: utf-8 -*-

__all__ = ["main"]

import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from functools import partial
from typing import Optional, Tuple

import click

from .unladen_version import version as __version__


class RefKind(Enum):
    UNKNOWN = 0
    TAG = 1
    BRANCH = 2


@dataclass
class RefInfo:
    name: str
    kind: RefKind


out = partial(click.secho, err=True)
err = partial(click.secho, fg="red", err=True)


@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
@click.version_option(version=__version__)
@click.option("-v", "--verbose", is_flag=True, help="Log more verbosely.")
@click.option("-r", "--ref", type=str, help="The git ref that is being built.")
@click.argument(
    "src",
    nargs=-1,
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
        allow_dash=True,
    ),
    is_eager=True,
)
@click.pass_context
def main(
    ctx: click.Context,
    verbose: Optional[bool],
    ref: Optional[str],
    src: Tuple[str, ...],
) -> None:
    log = partial(write_log, verbose=verbose)
    if not ref:
        ref = get_ref(ctx=ctx)
    log(f"Initial ref: {ref}")

    parsed_ref = parse_ref(ref)
    log(f"Parsed ref: {parsed_ref.name}")


def write_log(msg: str, verbose: bool = False) -> None:
    if verbose:
        out(msg)


def parse_ref(ref: str) -> RefInfo:
    if ref.startswith("refs/tags/"):
        return RefInfo(name=ref[10:], kind=RefKind.TAG)
    if ref.startswith("refs/heads/"):
        return RefInfo(name=ref[11:], kind=RefKind.BRANCH)
    return RefInfo(name=ref, kind=RefKind.UNKNOWN)


def get_ref(*, ctx: click.Context) -> str:
    ref = os.environ.get("GITHUB_REF", "").strip()
    if not ref:
        proc = subprocess.run(
            "git symbolic-ref -q HEAD || git describe --tags --exact-match",
            shell=True,
            capture_output=True,
        )
        if proc.returncode:
            err("💔 Couldn't infer git ref; make sure you're in a git repo")
            ctx.exit(1)
        ref = proc.stdout.decode("utf-8").strip()
    return ref
