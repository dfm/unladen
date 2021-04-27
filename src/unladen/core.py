# -*- coding: utf-8 -*-

__all__ = ["main"]

import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
from dataclasses import dataclass
from enum import Enum
from functools import partial
from pathlib import Path
from typing import Optional

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
@click.option("--ref", type=str, help="The git ref that is being built.")
@click.option(
    "--target",
    type=click.Path(file_okay=False, dir_okay=True),
    help="The target git repository for the output.",
)
@click.option(
    "--repo",
    type=str,
    help="The target git repository for the output.",
)
@click.option(
    "-b",
    "--branch",
    type=str,
    default="gh-pages",
    help="The branch to use on the target repository.",
    show_default=True,
)
@click.argument(
    "source",
    type=click.Path(
        exists=True,
        readable=True,
        file_okay=False,
        dir_okay=True,
    ),
)
@click.pass_context
def main(
    ctx: click.Context,
    verbose: bool,
    ref: Optional[str],
    target: Optional[str],
    repo: Optional[str],
    branch: str,
    source: str,
) -> None:
    if repo and target:
        err("Only one of 'repo' and 'target' can be specified")
        ctx.exit(1)
    if not (repo or target):
        err("Either 'repo' or 'target' must be specified")
        ctx.exit(1)

    # First get and parse the git ref
    if not ref:
        ref = get_ref(ctx=ctx, verbose=verbose)
    parsed_ref = parse_ref(ctx=ctx, ref=ref, verbose=verbose)
    if verbose:
        out(f"Using git ref: '{parsed_ref.name}' (parsed from '{ref}')")

    # Copy files
    source_dir = Path(source).resolve()

    if repo:
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir)
            checkout_or_init_repo(
                ctx=ctx,
                repo=repo,
                branch=branch,
                cwd=target_dir,
                verbose=verbose,
            )
            copy_source_to_target(
                ctx=ctx,
                source=source_dir,
                target=target_dir,
                ref=parsed_ref,
                verbose=verbose,
            )

    else:
        assert target is not None
        target_dir = Path(target).resolve()
        copy_source_to_target(
            ctx=ctx,
            source=source_dir,
            target=target_dir,
            ref=parsed_ref,
            verbose=verbose,
        )


def parse_ref(
    *, ctx: click.Context, ref: str, verbose: bool = False
) -> RefInfo:
    if ref.startswith("refs/tags/"):
        return RefInfo(name=slugify(ref[10:]), kind=RefKind.TAG)
    if ref.startswith("refs/heads/"):
        return RefInfo(name=slugify(ref[11:]), kind=RefKind.BRANCH)
    if verbose:
        err(f"Unrecognized ref format: {ref}")
    return RefInfo(name=ref, kind=RefKind.UNKNOWN)


def get_ref(*, ctx: click.Context, verbose: bool = False) -> str:
    ref = os.environ.get("GITHUB_REF", "").strip()
    if not ref:
        proc = subprocess.run(
            "git symbolic-ref -q HEAD || git describe --tags --exact-match",
            shell=True,
            capture_output=True,
        )
        if proc.returncode:
            err(
                "💔 Couldn't infer the git ref; make sure you're in a git repo!"
            )
            ctx.exit(1)
        ref = proc.stdout.decode("utf-8").strip()
    return ref


def checkout_or_init_repo(
    *,
    ctx: click.Context,
    repo: str,
    branch: str,
    cwd: Path,
    verbose: bool = False,
) -> None:
    run = partial(subprocess.run, cwd=cwd, capture_output=True)

    # Initialize the repo and fetch from the remote
    run(["git", "init"], check=True)
    run(["git", "remote", "add", "upstream", repo], check=True)
    proc: subprocess.CompletedProcess = run(
        ["git", "fetch", "upstream"], cwd=cwd
    )
    if proc.returncode:
        err(f"💔 Couldn't fetch git repo from {repo}")
        if verbose:
            err(
                " -> Full output from `git fetch`:\n\n"
                f"{proc.stderr.decode('utf-8')}"
            )
        ctx.exit(1)

    # Either checkout the right branch or create it
    proc = run(["git", "checkout", "-b", branch, f"upstream/{branch}"])
    if proc.returncode:
        if verbose:
            out(f"Checkout of {branch} failed; creating it fresh")
        run(["git", "checkout", "--orphan", branch], check=True)
        run(["git", "commit", "--allow-empty", "-m", '"Initial empty commit"'])


def copy_source_to_target(
    *,
    ctx: click.Context,
    source: Path,
    target: Path,
    ref: RefInfo,
    verbose: bool = False,
) -> None:
    target.mkdir(parents=True, exist_ok=True)
    fullpath = target / ref.name

    # Delete any existing directory or file at the target path
    if fullpath.exists():
        if verbose:
            out(f"{fullpath} exists, overwriting")
        if fullpath.is_dir():
            shutil.rmtree(fullpath)
        else:
            fullpath.unlink()

    # Do the copy
    shutil.copytree(source, fullpath)


def slugify(value: str) -> str:
    # ref: Django
    value = str(value)
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")
